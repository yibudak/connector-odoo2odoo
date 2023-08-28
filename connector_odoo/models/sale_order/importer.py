# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class SaleOrderBatchImporter(Component):
    """Import the Odoo Sale Orders.

    For every sale order in the list, a delayed job is created.
    A priority is set on the jobs according to their level to rise the
    chance to have the top level pricelist imported first.
    """

    _name = "odoo.sale.order.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.sale.order"]
    _usage = "batch.importer"

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        updated_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo sale orders %s returned %s items",
            domain,
            len(updated_ids),
        )
        base_priority = 10
        for order in updated_ids:
            order_id = self.backend_adapter.read(order)
            job_options = {
                "priority": base_priority,
            }
            self._import_record(order_id.id, job_options=job_options)


class SaleOrderImportMapper(Component):
    _name = "odoo.sale.order.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.sale.order"

    direct = [
        ("date_order", "backend_date_order"),
        ("name", "name"),
        ("state", "backend_state"),
    ]

    @mapping
    def backend_amount_total(self, record):
        return {"backend_amount_total": record.amount_total}

    @mapping
    def backend_amount_tax(self, record):
        return {"backend_amount_tax": record.amount_tax}

    @mapping
    def backend_picking_count(self, record):
        return {"backend_picking_count": len(record.picking_ids)}

    @only_create
    @mapping
    def odoo_id(self, record):
        order = self.env["sale.order"].search([("name", "=", record.name)])
        _logger.info("found sale order %s for record %s" % (record.name, record))
        if len(order) == 1:
            return {"odoo_id": order.id}

        return {}

    @mapping
    def pricelist_id(self, record):
        binder = self.binder_for("odoo.product.pricelist")
        pricelist_id = binder.to_internal(record.pricelist_id.id, unwrap=True)
        return {"pricelist_id": pricelist_id.id}

    @mapping
    def partner_id(self, record):
        binder = self.binder_for("odoo.res.partner")
        if self.backend_record.version != "6.1":
            return {
                "partner_id": binder.to_internal(record.partner_id.id, unwrap=True).id,
                "partner_invoice_id": binder.to_internal(
                    record.partner_invoice_id.id, unwrap=True
                ).id,
                "partner_shipping_id": binder.to_internal(
                    record.partner_shipping_id.id, unwrap=True
                ).id,
            }
        else:
            binder_address = self.binder_for("odoo.res.partner.address.disappeared")
            return {
                "partner_id": binder.to_internal(record.partner_id.id, unwrap=True).id,
                "partner_invoice_id": binder_address.to_internal(
                    record.partner_invoice_id.id, unwrap=True
                ).id,
                "partner_shipping_id": binder_address.to_internal(
                    record.partner_shipping_id.id, unwrap=True
                ).id,
            }


class SaleOrderImporter(Component):
    _name = "odoo.sale.order.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.sale.order"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        self._import_dependency(
            self.odoo_record.pricelist_id.id, "odoo.product.pricelist", force=force
        )
        self._import_dependency(
            self.odoo_record.partner_id.id, "odoo.res.partner", force=force
        )
        if self.backend_record.version != "6.1":
            for partner_id in [
                self.odoo_record.partner_shipping_id,
                self.odoo_record.partner_invoice_id,
            ]:
                self._import_dependency(partner_id.id, "odoo.res.partner", force=force)
        else:
            for address_id in [
                self.odoo_record.partner_shipping_id,
                self.odoo_record.partner_invoice_id,
            ]:
                self._import_dependency(
                    address_id.partner_id.id,
                    "odoo.res.partner.address.disappeared",
                    force=force,
                )

    def _after_import(self, binding, force=False):
        res = super()._after_import(binding, force)
        if self.odoo_record.order_line:
            delayed_line_ids = []
            for line_id in self.odoo_record.order_line:
                order_line_model = self.env["odoo.sale.order.line"]
                if self.backend_record.delayed_import_lines:
                    order_line_model = order_line_model.with_delay()
                delayed_line_id = order_line_model.import_record(
                    self.backend_record, line_id.id, force
                )
                if self.backend_record.delayed_import_lines:
                    delayed_line_id = self.env["queue.job"].search(
                        [("uuid", "=", delayed_line_id.uuid)]
                    )
                    delayed_line_ids.append(delayed_line_id.id)
            if self.backend_record.delayed_import_lines:
                binding.queue_job_ids = [
                    (6, 0, (delayed_line_ids + binding.queue_job_ids.ids))
                ]
        if not self.backend_record.delayed_import_lines:
            binding._set_state()
            self.env["odoo.stock.picking"].with_delay().import_batch(
                self.backend_record,
                [("sale_id", "=", self.odoo_record.id)],
            )
        return res
