import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AccountAccountBatchImporter(Component):
    """Import the Odoo Account Account.

    For every Account Account in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.account.account.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.account.account"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo Account Account %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options, force=force)


class AccountAccountImportMapper(Component):
    _name = "odoo.account.account.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.account.account"]

    direct = [
        ("code", "code"),
        ("name", "name"),
        ("reconcile", "reconcile"),
        ("note", "note"),
        ("deprecated", "deprecated"),
    ]

    @only_create
    @mapping
    def check_account_account_exists(self, record):
        res = {}
        account_id = self.env["account.account"].search([("code", "=", record["code"])])
        if len(account_id) == 1:
            _logger.info(
                "Account Account found for %s : %s" % (record["code"], account_id.code)
            )
            res.update({"odoo_id": account_id.id})
        return res

    @mapping
    def currency_id(self, record):
        vals = {}
        if record.get("currency_id"):
            binder = self.binder_for("odoo.res.currency")
            currency_id = binder.to_internal(record["currency_id"][0], unwrap=True)
            vals.update({"currency_id": currency_id.id})
        return vals

    @mapping
    def user_type_id(self, record):
        """Account types is not modelized in Odoo 16.
        So we are mapping available account types from v12.0"""
        vals = {}
        available_types = map(
            lambda f: f[0],
            self.env["account.account"]._fields["account_type"].selection,
        )
        if record["user_type_id"]:
            external_type = self.work.odoo_api.browse(
                model="account.account.type", res_id=record["user_type_id"][0]
            )
            if external_type["type"] in available_types:
                vals = {"account_type": external_type["type"]}
            else:
                vals = {"account_type": "income_other"}
        return vals

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}

    @mapping
    def group_id(self, record):
        vals = {}
        if record.get("group_id"):
            binder = self.binder_for("odoo.account.group")
            group_id = binder.to_internal(record["group_id"][0], unwrap=True)
            vals.update({"group_id": group_id.id})
        return vals


class AccountAccountImporter(Component):
    _name = "odoo.account.account.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.account.account"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if currency_id := record.get("currency_id"):
            self._import_dependency(
                currency_id[0], "odoo.res.currency", force=force
            )
        self._import_dependency(record["group_id"][0], "odoo.account.group", force=force)
        # for tax_id in record.tax_ids:
        #     self._import_dependency(tax_id.id, "odoo.account.tax", force=force)

    def _must_skip(self):
        return self.env["account.account"].search(
            [("code", "=", self.odoo_record["code"])]
        )

    # def _before_import(self):
    #     account_id = self.env["account.account"].search(
    #         [("code", "=", self.odoo_record.code)]
    #     )
    #     if not account_id:
    #         account_lenght = self.env.user.company_id.chart_template_id.code_digits
    #         account_code = self.odoo_record.code[:3]
    #         origing_account_id = self.env["account.account"].search(
    #             [("code", "=", account_code + ("0" * (account_lenght - 3)))]
    #         )
    #         if not origing_account_id:
    #             raise ValidationError(
    #                 _("Account Origin %s not found") % self.odoo_record.code
    #             )
    #         else:
    #             self.work.origing_account_id = origing_account_id
