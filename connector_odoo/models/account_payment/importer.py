# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AccountPaymentBatchImporter(Component):
    _name = "odoo.account.payment.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.account.payment"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo account payment %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class AccountPaymentMapper(Component):
    _name = "odoo.account.payment.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.account.payment"

    direct = [
        ("name", "name"),
        ("amount", "amount"),
        ("communication", "ref"),
        ("payment_type", "payment_type"),
        ("partner_type", "partner_type"),
    ]

    @mapping
    def partner_id(self, record):
        binder = self.binder_for("odoo.res.partner")
        partner_id = binder.to_internal(record["partner_id"][0], unwrap=True)
        return {"partner_id": partner_id.id}

    @mapping
    def currency_id(self, record):
        binder = self.binder_for("odoo.res.currency")
        currency_id = binder.to_internal(record["currency_id"][0], unwrap=True)
        return {"currency_id": currency_id.id}


class AccountPaymentImporter(Component):
    """Import Payment"""

    _name = "odoo.account.payment.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.account.payment"

    def _init_import(self, binding, external_id):
        # We should SKIP the payment import.
        return False

    def _import_dependencies(self, force=False):
        self._import_dependency(
            self.odoo_record["partner_id"][0],
            "odoo.res.partner",
            force=force,
        )
        if tx_id := self.odoo_record.get("payment_transaction_id"):
            self._import_dependency(
                tx_id[0],
                "odoo.payment.transaction",
                force=force,
            )
        return super()._import_dependencies(force=force)
