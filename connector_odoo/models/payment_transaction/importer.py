# Copyright 2022 Greenice, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class PaymentTransactionBatchImporter(Component):
    _name = "odoo.payment.transaction.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.payment.transaction"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo payment transaction %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class PaymentTransactionMapper(Component):
    _name = "odoo.payment.transaction.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.payment.transaction"

    direct = [
        ("garanti_xid", "garanti_xid"),
        ("garanti_secure3d_hash", "garanti_secure3d_hash"),
        ("callback_hash", "callback_hash"),
        ("reference", "reference"),
        ("amount", "amount"),
        ("state", "state"),
        ("partner_email", "partner_email"),
        ("partner_phone", "partner_phone"),
        ("partner_address", "partner_address"),
    ]

    @mapping
    def currency_id(self, record):
        binder = self.binder_for("odoo.res.currency")
        currency_id = binder.to_internal(record["currency_id"][0], unwrap=True)
        return {"currency_id": currency_id.id}

    @mapping
    def partner_id(self, record):
        binder = self.binder_for("odoo.res.partner")
        partner_id = binder.to_internal(record["partner_id"][0], unwrap=True)
        return {"partner_id": partner_id.id}

    @mapping
    def sale_order_ids(self, record):
        binder = self.binder_for("odoo.sale.order")
        order_list = []
        if sale_order_ids := record.get("sale_order_ids"):
            for order_id in sale_order_ids:
                order_list.append(binder.to_internal(order_id, unwrap=True).id)
        return {"sale_order_ids": [(6, 0, order_list)]}

    @mapping
    def payment_id(self, record):
        vals = {"payment_id": False}
        if payment_id := record.get("payment_id"):
            binder = self.binder_for("odoo.account.payment")
            vals["payment_id"] = binder.to_internal(payment_id[0], unwrap=True).id
        return vals


class PaymentTransactionImporter(Component):
    """Import Payment Transaction"""

    _name = "odoo.payment.transaction.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.payment.transaction"

    def _import_dependencies(self, force=False):
        self._import_dependency(
            self.odoo_record["partner_id"][0],
            "odoo.res.partner",
            force=force,
        )
        return super()._import_dependencies(force=force)
