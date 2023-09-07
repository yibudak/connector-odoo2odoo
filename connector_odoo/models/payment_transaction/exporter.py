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
        # ("callback_hash", "callback_hash"), # todo: yigit fix permission issue and enable this line.
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
        return {"acquirer_id": 29}  # Garanti Sanal POS

    @mapping
    def partner_id(self, record):
        # yigit partnert export_dependencies'de export etmek gerekir mi
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
        ext_counry = self.work.odoo_api.search(
            model="res.country",
            domain=[("code", "=", record.partner_country_id.code)],
            fields=["id"],
        )
        return {
            "partner_country_id": ext_counry[0]["id"],
        }

    @mapping
    def sale_order_ids(self, record):
        binder = self.binder_for("odoo.sale.order")
        orders = []
        for order in record.sale_order_ids:
            orders.append(binder.to_external(order, wrap=True))
        return {
            "sale_order_ids": [(6, 0, orders)],
        }

    @mapping
    def payment_id(self, record):
        vals = {}
        if record.payment_id:
            binder = self.binder_for("odoo.account.payment")
            vals["payment_id"] = binder.to_external(record.payment_id, wrap=True)
        return vals


class OdooPaymentTransactionExporter(Component):
    _name = "odoo.payment.transaction.exporter"
    _inherit = "odoo.exporter"
    _apply_on = ["odoo.payment.transaction"]

    def _export_dependencies(self):
        if self.binding.payment_id:
            self._export_dependency(self.binding.payment_id, "odoo.account.payment")
        if self.binding.partner_id:
            self._export_dependency(self.binding.partner_id, "odoo.res.partner")

    def _after_export(self):
        # Update payment_id's transaction_id
        payment_binding = self.env["odoo.account.payment"].search(
            [
                ("backend_id", "=", self.backend_record.id),
                ("odoo_id", "=", self.binding.payment_id.id),
            ]
        )
        if payment_binding and payment_binding.external_id:
            self.work.odoo_api.write(
                model="account.payment",
                res_id=payment_binding.external_id,
                data={"payment_transaction_id": self.binding.external_id},
            )
        return True

    def _create_data(self, map_record, fields=None, **kwargs):
        """Get the data to pass to :py:meth:`_create`"""
        datas = map_record.values(for_create=True, fields=fields, **kwargs)
        return datas
