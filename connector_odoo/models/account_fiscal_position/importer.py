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

    def run(self, filters=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(filters)
        _logger.debug(
            "search for odoo Account Group %s returned %s items",
            filters,
            len(external_ids),
        )
        base_priority = 10
        for external_id in external_ids:
            job_options = {"priority": base_priority}
            self._import_record(external_id, job_options=job_options, force=force)


class AccountFiscalPositionImportMapper(Component):
    _name = "odoo.account.fiscal.position.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.account.fiscal.position"]

    direct = [
        ("name", "name"),
        ("auto_apply", "auto_apply"),
        ("note", "note"),
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
                    ("name", "=", record.name),
                ],
                limit=1,
            )
        )
        if fp_record:
            _logger.debug(
                "Account Fiscal Position found for %s : %s" % (record, fp_record)
            )
            res.update({"odoo_id": fp_record.id})
        return res

    @mapping
    def tax_ids(self, record):
        """Actually we can map fiscal.position.tax but importing fiscal positions
         is not common so much."""
        vals = {}
        binder = self.binder_for("odoo.account.tax")
        if record.tax_ids:
            taxes = []
            for tax_line in record.tax_ids:
                src_tax = binder.to_internal(tax_line.tax_src_id.id, unwrap=True)
                dest_tax = binder.to_internal(tax_line.tax_dest_id.id, unwrap=True)
                create_vals = {
                    "tax_src_id": src_tax.id,
                    "tax_dest_id": dest_tax.id,
                }
                taxes.append((0, 0, create_vals))
            vals.update({"tax_ids": taxes})
        return vals

    @mapping
    def account_ids(self, record):
        """Actually we can map fiscal.position.account but importing fiscal positions
         is not common so much."""
        vals = {}
        binder = self.binder_for("odoo.account.account")
        if record.account_ids:
            accounts = []
            for account_line in record.account_ids:
                src_account = binder.to_internal(
                    account_line.account_src_id.id, unwrap=True
                )
                dest_account = binder.to_internal(
                    account_line.account_dest_id.id, unwrap=True
                )
                vals = {
                    "account_src_id": src_account.id,
                    "account_dest_id": dest_account.id,
                }
                accounts.append((0, 0, vals))
            vals.update({"account_ids": accounts})
        return vals


class AccountFiscalPositionImporter(Component):
    _name = "odoo.account.fiscal.position.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.account.fiscal.position"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if record.tax_ids:
            src_taxes = [x.tax_src_id for x in record.tax_ids]
            dest_taxes = [x.tax_dest_id for x in record.tax_ids]
            for tax in (src_taxes + dest_taxes):
                self._import_dependency(tax.id, "odoo.account.tax", force=force)

        if record.account_ids:
            src_accounts = [x.account_src_id for x in record.account_ids]
            dest_accounts = [x.account_dest_id for x in record.account_ids]
            for account in (src_accounts + dest_accounts):
                self._import_dependency(account.id, "odoo.account.account", force=force)
