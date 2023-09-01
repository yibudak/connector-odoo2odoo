# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import only_create, mapping

_logger = logging.getLogger(__name__)


class OdooSaleOrderExporter(Component):
    _name = "odoo.sale.order.exporter"
    _inherit = "odoo.exporter"
    _apply_on = ["odoo.sale.order"]

    # Todo yigit: enable this
    # def _must_skip(self):
    #     """If there is no USER on the sale order, this means that guest user creates the
    #     order. We don't want to export it."""
    #     return not (self.binding.partner_id.user_id or self.binding.partner_id.user_ids)

    def _export_dependencies(self):
        if not self.binding.partner_id:
            return

        partner_records = self.env["res.partner"]
        partner_fields = ["partner_id", "partner_invoice_id", "partner_shipping_id"]

        # try to collect all partners
        for field in partner_fields:
            partner_records |= self.binding[field]

        for record_partner in partner_records:
            self._export_dependency(record_partner, "odoo.res.partner")

    def _after_export(self):
        """Hook called after the export"""
        binding = self.binding
        if binding and binding.order_line:
            for line in binding.order_line:
                self._export_dependency(line, "odoo.sale.order.line")
        # if binding and binding.transaction_ids:
        #     for tx in binding.transaction_ids:
        #         self._export_dependency(tx, "odoo.payment.transaction")


class SaleOrderExportMapper(Component):
    _name = "odoo.sale.order.export.mapper"
    _inherit = "odoo.export.mapper"
    _apply_on = ["odoo.sale.order"]

    direct = [
        ("name", "name"),
        # ("state", "state"),
    ]

    # yigit: buraya artık gerek yok cunku sale.order.line'ı mapledik.
    # children = [("order_line", "order_line", "odoo.sale.order.line")]

    @only_create
    @mapping
    def state_create(self, record):
        """
        Durumu taslak olarak göndermeliyiz ki böylece action_confirm çağrıldığında
        durum düzgün bir şekilde güncellensin.
        """
        return {"state": "draft"}

    @mapping
    def state(self, record):
        return {"state": record.state}

    @mapping
    def date_order(self, record):
        return {
            "date_order": record.date_order.strftime(DEFAULT_SERVER_DATETIME_FORMAT)
        }

    @mapping
    def pricelist_id(self, record):
        binder = self.binder_for("odoo.product.pricelist")
        pricelist_id = binder.to_external(record.pricelist_id, wrap=True)
        return {"pricelist_id": pricelist_id or 123}  # 123: Genel Fiyat Listesi

    @mapping
    def warehouse_id(self, record):
        binder = self.binder_for("odoo.stock.warehouse")
        warehouse_id = binder.to_external(record.warehouse_id, wrap=True)
        return {"warehouse_id": 2}  # Todo

    @mapping
    def partner_id(self, record):
        binder = self.binder_for("odoo.res.partner")
        return {
            "partner_id": binder.to_external(
                record.partner_id,
                wrap=True,
            ),
            "partner_invoice_id": binder.to_external(
                record.partner_invoice_id,
                wrap=True,
            ),
            "partner_shipping_id": binder.to_external(
                record.partner_shipping_id,
                wrap=True,
            ),
        }

    @mapping
    def carrier_id(self, record):
        binder = self.binder_for("odoo.delivery.carrier")
        return {"carrier_id": binder.to_external(record.carrier_id, wrap=True)}

    @mapping
    def client_order_ref(self, record):
        # Todo: müşterinin satınalma numarası için bir field yapılacak
        return {"client_order_ref": "E-commerce sale"}

    # todo: confirmation_date action_confirm ile oluşturulup gönderilecek. Belki de
    # göndermeye gerek yok karşıda action_confirm çalıştırırsak problem çözülür.
    # @mapping
    # def confirmation_date(self, record):
    #     return {
    #         "confirmation_date": datetime.now().strftime(DEFAULT_SERVER_DATETIME_FORMAT)
    #     }
