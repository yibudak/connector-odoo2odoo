import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AccountPaymentTermBatchImporter(Component):
    """Import the Odoo Account Payment Term.

    For every Account Group in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.account.payment.term.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.account.payment.term"]

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


class AccountPaymentTermImportMapper(Component):
    _name = "odoo.account.payment.term.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.account.payment.term"]

    direct = [
        ("name", "name"),
        ("note", "note"),
        ("active", "active"),
        ("use_risk_credit_limit", "use_risk_credit_limit"),
    ]

    # @only_create
    # @mapping
    # def check_account_fiscal_position_exists(self, record):
    #     res = {}
    #     ctx = {"lang": self.backend_record.get_default_language_code()}
    #     pt_record = (
    #         self.env["account.payment.term"]
    #         .with_context(ctx)
    #         .search(
    #             [
    #                 ("name", "=", record["name"]),
    #             ],
    #             limit=1,
    #         )
    #     )
    #     if pt_record:
    #         _logger.info(
    #             "Account Fiscal Position found for %s : %s"
    #             % (record["name"], pt_record)
    #         )
    #         res.update({"odoo_id": pt_record.id})
    #     return res

    # @mapping
    # def line_ids(self, record):
    #     res = {}
    #     if record.line_ids:
    #         lines = []
    #         for line in record.line_ids:
    #             create_vals = {
    #                 "value": line.value,
    #                 "value_amount": line.value_amount,
    #                 "days": line.days,
    #             }
    #             lines.append((0, 0, create_vals))
    #         res.update({"line_ids": lines})
    #     return res


class AccountPaymentTermImporter(Component):
    _name = "odoo.account.payment.term.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.account.payment.term"]
