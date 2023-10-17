import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AccountTaxBatchImporter(Component):
    """Import the Odoo Account Group.

    For every Account Group in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.account.tax.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.account.tax"]

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


class AccountTaxImportMapper(Component):
    _name = "odoo.account.tax.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.account.tax"]

    direct = [
        ("name", "name"),
        ("amount", "amount"),
        ("type_tax_use", "type_tax_use"),
        ("description", "description"),
        ("active", "active"),
    ]

    @only_create
    @mapping
    def check_account_tax_exists(self, record):
        res = {}
        ctx = {"lang": self.backend_record.get_default_language_code()}
        tax_record = (
            self.env["account.tax"]
            .with_context(ctx)
            .search(
                [
                    ("name", "=", record["name"]),
                    ("type_tax_use", "=", record["type_tax_use"]),
                ],
                limit=1,
            )
        )
        if tax_record:
            _logger.info("Account Tax found for %s : %s" % (record, tax_record))
            res.update({"odoo_id": tax_record.id})
        return res

    @mapping
    def country_id(self, record):
        return {"country_id": self.env.ref("base.tr").id}

    # @mapping
    # def account_id(self, record):
    #     vals = {}
    #     if record.account_id:
    #         binder = self.binder_for("odoo.account.account")
    #         account = binder.to_internal(record.account_id.id, unwrap=True)
    #         if account:
    #             vals.update({"account_id": account.id})
    #     return vals
    #
    # @mapping
    # def refund_account_id(self, record):
    #     vals = {}
    #     if record.refund_account_id:
    #         binder = self.binder_for("odoo.account.account")
    #         account = binder.to_internal(record.refund_account_id.id, unwrap=True)
    #         if account:
    #             vals.update({"refund_account_id": account.id})
    #     return vals

    @mapping
    def tax_group_id(self, record):
        vals = {}
        if tax_group_id := record["tax_group_id"]:
            binder = self.binder_for("odoo.account.tax.group")
            local_tax_group_id = binder.to_internal(tax_group_id[0], unwrap=True)
            if local_tax_group_id:
                vals.update({"tax_group_id": local_tax_group_id.id})
        return vals

    @mapping
    def children_tax_ids(self, record):
        vals = {"children_tax_ids": []}
        if record["amount_type"] == "group":
            if children_tax_ids := record.get("children_tax_ids"):
                binder = self.binder_for("odoo.account.tax")
                children = []
                for tax_id in children_tax_ids:
                    if local_tax := binder.to_internal(tax_id, unwrap=True):
                        children.append(local_tax.id)
                vals["children_tax_ids"] = [(6, 0, children)]
        return vals


class AccountTaxImporter(Component):
    _name = "odoo.account.tax.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.account.tax"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if tax_group_id := record.get("tax_group_id"):
            self._import_dependency(
                tax_group_id[0], "odoo.account.tax.group", force=force
            )
        # if record.account_id:
        #     self._import_dependency(
        #         record.account_id.id, "odoo.account.account", force=force
        #     )
        # if record.refund_account_id:
        #     self._import_dependency(
        #         record.refund_account_id.id, "odoo.account.account", force=force
        #     )
        #  Grouped taxes
        if record.get("amount_type") == "group":
            for tax_id in record.get("children_tax_ids"):
                self._import_dependency(tax_id, "odoo.account.tax", force=force)
