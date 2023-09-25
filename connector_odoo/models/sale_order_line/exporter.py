# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from datetime import datetime
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import ExportMapChild, mapping

_logger = logging.getLogger(__name__)


class BatchSaleOrderLineExporter(Component):
    _name = "odoo.sale.order.line.batch.exporter"
    _inherit = "odoo.delayed.batch.exporter"
    _apply_on = ["odoo.sale.order.line"]
    _usage = "batch.exporter"


class SaleOrderLineExportMapper(Component):
    _name = "odoo.sale.order.line.export.mapper"
    _inherit = "odoo.export.mapper"
    _apply_on = ["odoo.sale.order.line"]

    direct = [
        ("discount", "discount"),
        ("price_unit", "price_unit"),
        ("product_uom_qty", "product_uom_qty"),
        ("is_delivery", "is_delivery"),
        ("deci", "deci"),
    ]

    @mapping
    def product_id(self, record):
        binder = self.binder_for("odoo.product.product")
        return {
            "product_id": binder.to_external(record.product_id, wrap=True),
        }

    @mapping
    def set_parent_product_id(self, record):
        vals = {}
        binder = self.binder_for("odoo.product.product")
        if record.set_parent_product_id:
            vals["set_parent_product_id"] = binder.to_external(
                record.set_parent_product_id, wrap=True
            )
        return vals

    @mapping
    def name(self, record):
        return {
            "name": record.product_id.display_name,
        }

    @mapping
    def order_id(self, record):
        binder = self.binder_for("odoo.sale.order")
        return {
            "order_id": binder.to_external(record.order_id, wrap=True),
        }

    @mapping
    def product_uom(self, record):
        binder = self.binder_for("odoo.uom.uom")
        return {
            "product_uom": binder.to_external(record.product_uom, wrap=True),
        }

    @mapping
    def tax_id(self, record):
        binder = self.binder_for("odoo.account.tax")
        taxes = []
        for tax in record.tax_id:
            external_id = binder.to_external(tax, wrap=True)
            if external_id:
                taxes.append(external_id)
        return {"tax_id": [(6, 0, taxes)]}


class OdooSaleOrderLineExporter(Component):
    _name = "odoo.sale.order.line.exporter"
    _inherit = "odoo.exporter"
    _apply_on = ["odoo.sale.order.line"]

    def _should_import(self):
        """If we don't have any external_id in order_line, and we could match
        a record with specific elements, we should write it to Odoo."""
        if not self.external_id:
            external_order = self.backend_adapter.search(
                model="sale.order",
                domain=[("name", "=", self.binding.order_id.name)],
                limit=1,
            )
            if external_order:
                possible_line = self.backend_adapter.search(
                    model="sale.order.line",
                    domain=[
                        ("order_id", "=", external_order[0]),
                        (
                            "product_id",
                            "in",
                            self.binding.mapped("product_id.bind_ids.external_id"),
                        ),
                    ],
                    limit=1,
                )
                if possible_line:
                    self.external_id = possible_line[0]
        return super(OdooSaleOrderLineExporter, self)._should_import()

    def _create_data(self, map_record, fields=None, **kwargs):
        """Get the data to pass to :py:meth:`_create`"""
        datas = map_record.values(for_create=True, fields=fields, **kwargs)
        return datas
