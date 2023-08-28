# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class SaleOrderLineBatchImporter(Component):
    """Import the Odoo Sale Order Lines.

    For every pricelist item in the list, a delayed job is created.
    """

    _name = "odoo.sale.order.line.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.sale.order.item"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        updated_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo sale orders %s returned %s items",
            domain,
            len(updated_ids),
        )
        for order in updated_ids:
            order_id = self.backend_adapter.read(order)
            job_options = {
                "priority": 10,
            }
            self._import_record(order_id.id, job_options=job_options)


class SaleOrderLineImportMapper(Component):
    _name = "odoo.sale.order.line.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.sale.order.line"

    direct = [
        ("name", "name"),
        ("price_unit", "price_unit"),
        ("product_uom_qty", "product_uom_qty"),
        ("product_qty", "product_qty"),
        ("display_type", "display_type"),
        ("customer_lead", "customer_lead"),
        ("discount", "discount"),
    ]

    @mapping
    def product_id(self, record):
        binder = self.binder_for("odoo.product.product")
        return {
            "product_id": binder.to_internal(record.product_id.id, unwrap=True).id,
        }

    @mapping
    def order_id(self, record):
        binder = self.binder_for("odoo.sale.order")
        return {
            "order_id": binder.to_internal(record.order_id.id, unwrap=True).id,
        }

    @mapping
    def product_uom(self, record):
        binder = self.binder_for("odoo.uom.uom")
        return {
            "product_uom": binder.to_internal(record.product_uom.id, unwrap=True).id,
        }


class SaleOrderLineImporter(Component):
    _name = "odoo.sale.order.line.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.sale.order.line"]

    def _import_dependencies(self, force):
        self._import_dependency(
            self.odoo_record.product_id.id, "odoo.product.product", force=force
        )
        self._import_dependency(
            self.odoo_record.product_uom.id, "odoo.uom.uom", force=force
        )

    def _after_import(self, binding, force=False):
        res = super()._after_import(binding, force)
        if self.backend_record.delayed_import_lines:
            pending = binding.order_id.queue_job_ids.filtered(
                lambda x: x.state != "done" and x.args[1] != self.odoo_record.id
            )
            if not pending:
                binding = self.env["odoo.sale.order"].search(
                    [("odoo_id", "=", binding.order_id.id)]
                )
                if not len(binding.picking_ids):
                    binding._set_state()
                self.env["odoo.stock.picking"].with_delay().import_batch(
                    self.backend_record,
                    [("sale_id", "=", self.odoo_record.order_id.id)],
                )
        return res
