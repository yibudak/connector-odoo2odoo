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
    _apply_on = ["odoo.sale.order.line"]

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
            self._import_record(order_id.id, force=force)


class SaleOrderLineImportMapper(Component):
    _name = "odoo.sale.order.line.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.sale.order.line"

    direct = [
        ("name", "name"),
        ("price_unit", "price_unit"),
        ("product_uom_qty", "product_uom_qty"),
        ("product_qty", "product_qty"),
        ("is_delivery", "is_delivery"),
        ("display_type", "display_type"),
        ("customer_lead", "customer_lead"),
        ("discount", "discount"),
        ("deci", "deci"),
    ]

    @mapping
    def product_id(self, record):
        binder = self.binder_for("odoo.product.product")
        return {
            "product_id": binder.to_internal(record["product_id"][0], unwrap=True).id,
        }

    @mapping
    def order_id(self, record):
        binder = self.binder_for("odoo.sale.order")
        return {
            "order_id": binder.to_internal(record["order_id"][0], unwrap=True).id,
        }

    @mapping
    def product_uom(self, record):
        binder = self.binder_for("odoo.uom.uom")
        return {
            "product_uom": binder.to_internal(record["product_uom"][0], unwrap=True).id,
        }


class SaleOrderLineImporter(Component):
    _name = "odoo.sale.order.line.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.sale.order.line"]

    def _get_binding_with_data(self, binding):
        """Sometimes we have trouble with import-export sale.order.line. This method
        helps us find the binding record, so we prevent the creation of duplicate
        records.
        """
        binding = super(SaleOrderLineImporter, self)._get_binding_with_data(binding)
        if not binding:
            domain = [("backend_id", "=", self.backend_record.id)]
            if local_order := self.binder_for("odoo.sale.order").to_internal(
                self.odoo_record["order_id"][0], unwrap=True
            ):
                domain.append(("odoo_id", "=", local_order.id))
            if local_product := self.binder_for("odoo.product.product").to_internal(
                self.odoo_record["product_id"][0], unwrap=True
            ):
                domain.append(("product_id", "=", local_product.id))
            if local_product and local_order:
                binding = self.model.search(domain, limit=1)
        return binding

    def _import_dependencies(self, force):
        self._import_dependency(
            self.odoo_record["product_id"][0],
            "odoo.product.product",
            force=force,
        )
        self._import_dependency(
            self.odoo_record["product_uom"][0],
            "odoo.uom.uom",
            force=force,
        )

    def _get_context(self):
        """
        Do not create procurement for sale order lines.
        """
        ctx = super(SaleOrderLineImporter, self)._get_context()
        ctx["skip_procurement"] = True
        ctx["skip_price_recompute"] = True
        return ctx
