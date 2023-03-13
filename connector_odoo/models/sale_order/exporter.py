# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import ExportMapChild, mapping

# from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class OdooSaleOrderExporter(Component):
    _name = "odoo.sale.order.exporter"
    _inherit = "odoo.exporter"
    _apply_on = ["odoo.sale.order"]

    def _get_partner(self, record_partner):
        partner_ids = record_partner.bind_ids
        partner = self.env["odoo.res.partner"]
        if partner_ids:
            partner = partner_ids.filtered(
                lambda c: c.backend_id == self.backend_record
            )
        if not partner:
            partner = self.env["odoo.res.partner"].create(
                {
                    "odoo_id": record_partner.id,
                    "external_id": 0,  # Todo: check this violates not null constraint
                    "backend_id": self.backend_record.id,
                }
            )
        return partner

    def _export_dependencies(self):
        if not self.binding.partner_id:
            return

        partner_records = self.env["res.partner"]
        partner_fields = ["partner_id", "partner_invoice_id", "partner_shipping_id"]
        for field in partner_fields:
            partner_records |= self.binding[field]

        for record_partner in partner_records:
            partner = self._get_partner(record_partner)
            bind_partner = self.binder.to_external(partner, wrap=False)
            if not bind_partner:
                self._export_dependency(partner, "odoo.res.partner")


class SaleOrderExportMapper(Component):
    _name = "odoo.sale.order.export.mapper"
    _inherit = "odoo.export.mapper"
    _apply_on = ["odoo.sale.order"]

    direct = [
        ("name", "name"),
        ("state", "state"),
    ]

    children = [("order_line", "order_line", "odoo.sale.order.line")]

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
    def client_order_ref(self, record):
        # Todo: müşterinin satınalma numarası için bir field yapılacak
        return {"client_order_ref": "E-commerce sale"}


class SaleOrderLineExportMapper(Component):
    _name = "odoo.sale.order.line.export.mapper"
    _inherit = "odoo.export.mapper"
    _apply_on = ["odoo.sale.order.line"]

    direct = [
        ("name", "name"),
        ("price_unit", "price_unit"),
        ("product_uom_qty", "product_uom_qty"),
    ]

    @mapping
    def product_id(self, record):
        binder = self.binder_for("odoo.product.product")
        return {
            "product_id": binder.to_external(record.product_id, wrap=True),
        }


class SaleOrderExportMapChild(ExportMapChild):
    _model_name = "odoo.sale.order"

    def format_items(self, items_values):
        self
        items_values
        print("yifit")
        return [(0, 0, item) for item in items_values]
