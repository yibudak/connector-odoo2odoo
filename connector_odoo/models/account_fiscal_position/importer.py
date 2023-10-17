import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AccountFiscalPositionBatchImporter(Component):
    """Import the Odoo Account Group.

    For every Account Group in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.account.fiscal.position.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.account.fiscal.position"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo Account Group %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class AccountFiscalPositionImportMapper(Component):
    _name = "odoo.account.fiscal.position.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.account.fiscal.position"]

    direct = [
        ("name", "name"),
        ("auto_apply", "auto_apply"),
        ("note", "note"),
        ("active", "active"),
    ]

    @only_create
    @mapping
    def check_account_fiscal_position_exists(self, record):
        res = {}
        ctx = {"lang": self.backend_record.get_default_language_code()}
        fp_record = (
            self.env["account.fiscal.position"]
            .with_context(ctx)
            .search(
                [
                    ("name", "=", record["name"]),
                ],
                limit=1,
            )
        )
        if fp_record:
            _logger.info(
                "Account Fiscal Position found for %s : %s" % (record, fp_record)
            )
            res.update({"odoo_id": fp_record.id})
        return res


class AccountFiscalPositionImporter(Component):
    _name = "odoo.account.fiscal.position.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.account.fiscal.position"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if tax_ids := record.get("tax_ids"):
            fiscal_position_taxes = self.work.odoo_api.search(
                "account.fiscal.position.tax",
                domain=[
                    ("id", "in", tax_ids),
                ],
            )
            # map source and destination tax ids
            taxes_set = set(
                item
                for sublist in map(
                    lambda f: (f["tax_src_id"][0], f["tax_dest_id"][0]),
                    fiscal_position_taxes,
                )
                for item in sublist
            )
            for tax_id in list(taxes_set):
                self._import_dependency(tax_id, "odoo.account.tax", force=force)

        if account_ids := record.get("account_ids"):
            # todo: this part is missing.
            src_accounts = [x.account_src_id for x in record.account_ids]
            dest_accounts = [x.account_dest_id for x in record.account_ids]
            for account in src_accounts + dest_accounts:
                self._import_dependency(account.id, "odoo.account.account", force=force)

    def _after_import(self, binding, force=False):
        """Hook called at the end of the import"""
        res = super()._after_import(binding, force=force)
        # yigit: since we don't map line models, we need to import them after
        # the main record is imported
        self._import_tax_ids(binding)
        self._import_account_ids(binding)
        return res

    def _import_tax_ids(self, binding):
        """
        Manual import of tax_ids since we don't map the many2many model
        """
        if not self.odoo_record.get("tax_ids"):
            return False

        tax_lines = []
        tax_binder = self.binder_for("odoo.account.tax")

        for tax_line_id in self.odoo_record.get("tax_ids"):
            ext_tax_line = self.work.odoo_api.browse(
                model="account.fiscal.position.tax", res_id=tax_line_id
            )
            src_tax = tax_binder.to_internal(ext_tax_line["tax_src_id"][0], unwrap=True)
            dest_tax = tax_binder.to_internal(
                ext_tax_line["tax_dest_id"][0], unwrap=True
            )
            local_tax_line = self.env["account.fiscal.position.tax"].search(
                [
                    ("tax_src_id", "=", src_tax.id),
                    ("tax_dest_id", "=", dest_tax.id),
                    ("position_id", "=", binding.odoo_id.id),
                ]
            )
            if not local_tax_line:
                create_vals = {
                    "tax_src_id": src_tax.id,
                    "tax_dest_id": dest_tax.id,
                    "position_id": binding.odoo_id.id,
                }
                local_tax_line = self.env["account.fiscal.position.tax"].create(
                    create_vals
                )
            tax_lines.append(local_tax_line.id)

        binding.write({"tax_ids": [(6, 0, tax_lines)]})
        return True

    def _import_account_ids(self, binding):
        """
        Manual import of account_ids since we don't map the many2many model
        """
        if not self.odoo_record.get("account_ids"):
            return False

        account_lines = []
        account_binder = self.binder_for("odoo.account.account")

        for account_line in self.odoo_record.get("account_ids"):
            src_account = account_binder.to_internal(
                account_line.account_src_id.id, unwrap=True
            )
            dest_account = account_binder.to_internal(
                account_line.account_dest_id.id, unwrap=True
            )
            local_account_line = self.env["account.fiscal.position.account"].search(
                [
                    ("account_src_id", "=", src_account.id),
                    ("account_dest_id", "=", dest_account.id),
                    ("position_id", "=", binding.odoo_id.id),
                ]
            )
            if not local_account_line:
                create_vals = {
                    "account_src_id": src_account.id,
                    "account_dest_id": dest_account.id,
                    "position_id": binding.odoo_id.id,
                }
                local_account_line = self.env["account.fiscal.position.account"].create(
                    create_vals
                )
            account_lines.append(local_account_line.id)
