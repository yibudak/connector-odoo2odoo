# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class MrpBomLineBatchImporter(Component):
    """Import the BOM Lines."""

    _name = "odoo.mrp.bom.line.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.mrp.bom.line"]

    def run(self, filters=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(filters)
        imported_boms = self.env["odoo.mrp.bom"].search([]).mapped("external_id")
        filters.append(("bom_id", "in", imported_boms))
        _logger.info(
            "search for delivery regions %s returned %s items",
            filters,
            len(external_ids),
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options)


class MrpBomLineMapper(Component):
    _name = "odoo.mrp.bom.line.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.mrp.bom.line"]

    direct = [
        ("sequence", "sequence"),
        ("product_qty", "product_qty"),
    ]

    @mapping
    def bom_id(self, record):
        res = {}
        bom = record.bom_id
        if bom:
            local_bom = self.env["odoo.mrp.bom"].search(
                [("external_id", "=", bom.id)]
            )
            if local_bom:
                res["bom_id"] = local_bom.odoo_id.id
        return res

    @mapping
    def product_id(self, record):
        res = {}
        product = record.product_id
        if product:
            local_product = self.env["odoo.product.product"].search(
                [("external_id", "=", product.id)]
            )
            if local_product:
                res["product_id"] = local_product.odoo_id.id
        return res

    @mapping
    def product_tmpl_id(self, record):
        res = {}
        product = record.product_tmpl_id
        if product:
            local_product = self.env["odoo.product.template"].search(
                [("external_id", "=", product.id)]
            )
            if local_product:
                res["product_tmpl_id"] = local_product.odoo_id.id
        return res

    @mapping
    def product_uom_id(self, record):
        res = {}
        uom = record.product_uom_id
        if uom:
            local_uom = self.env["odoo.uom.uom"].search([("external_id", "=", uom.id)])
            if local_uom:
                res["product_uom_id"] = local_uom.odoo_id.id
        return res


class MrpBomLineImporter(Component):
    _name = "odoo.mrp.bom.line.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.mrp.bom.line"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        super()._import_dependencies(force=force)
        record = self.odoo_record
        # self._import_dependency(
        #     record.bom_id.id, "odoo.mrp.bom", force=force
        # )
        if record.product_tmpl_id:
            self._import_dependency(
                record.product_tmpl_id.id, "odoo.product.template", force=force
            )
        if record.product_id:
            self._import_dependency(
                record.product_id.id, "odoo.product.product", force=force
            )
