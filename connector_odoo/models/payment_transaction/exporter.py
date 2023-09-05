# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


class BatchPaymentTransactionExporter(Component):
    _name = "odoo.payment.transaction.batch.exporter"
    _inherit = "odoo.delayed.batch.exporter"
    _apply_on = ["odoo.payment.transaction"]
    _usage = "batch.exporter"


class PaymentTransactionExportMapper(Component):
    _name = "odoo.payment.transaction.export.mapper"
    _inherit = "odoo.export.mapper"
    _apply_on = ["odoo.payment.transaction"]

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
    def type(self, record):
        return {"type": "form"}

    @mapping
    def acquirer_id(self, record):
        pass
        # yigit elle map et

    @mapping
    def partner_id(self, record):
        # yigit partnert export_dependencies'de export et
        binder = self.binder_for("odoo.res.partner")
        return {
            "partner_id": binder.to_external(record.partner_id, wrap=True),
        }

    @mapping
    def currency_id(self, record):
        binder = self.binder_for("odoo.res.currency")
        return {
            "currency_id": binder.to_external(record.currency_id, wrap=True),
        }

    @mapping
    def partner_country_id(self, record):
        binder = self.binder_for("odoo.res.country")
        return {
            "partner_country_id": binder.to_external(
                record.partner_country_id, wrap=True
            ),
        }

    @mapping
    def sale_order_ids(self, record):
        binder = self.binder_for("odoo.sale.order")
        return {
            "sale_order_ids": [(6, 0, binder.to_external(record.sale_order_ids))],
        }

    @mapping
    def payment_id(self, record):
        pass


class OdooPaymentTransactionExporter(Component):
    _name = "odoo.payment.transaction.exporter"
    _inherit = "odoo.exporter"
    _apply_on = ["odoo.payment.transaction"]

    def _export_dependencies(self):
        if self.binding.payment_id:
            self._export_dependency(self.binding.payment_id, "odoo.account.payment")
        if self.binding.partner_id:
            self._export_dependency(self.binding.partner_id, "odoo.res.partner")

    def _create_data(self, map_record, fields=None, **kwargs):
        """Get the data to pass to :py:meth:`_create`"""
        datas = map_record.values(for_create=True, fields=fields, **kwargs)
        return datas
