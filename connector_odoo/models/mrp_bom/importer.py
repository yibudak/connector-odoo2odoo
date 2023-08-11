# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class MrpBomBatchImporter(Component):
    """Import the Mrp Boms."""

    _name = "odoo.mrp.bom.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.mrp.bom"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""
        imported_products = (
            self.env["odoo.product.template"].search([]).mapped("external_id")
        )
        domain.append(("product_tmpl_id", "in", imported_products))
        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for delivery regions %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options, force=force)


class MrpBomMapper(Component):
    _name = "odoo.mrp.bom.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.mrp.bom"]

    direct = [
        ("type", "type"),
        ("sequence", "sequence"),
        ("ready_to_produce", "ready_to_produce"),
        ("product_qty", "product_qty"),
        ("code", "code"),
        ("active", "active"),
    ]

    @mapping
    def product_uom_id(self, record):
        res = {}
        if uom := record.get("product_uom_id"):
            local_uom = self.env["odoo.uom.uom"].search([("external_id", "=", uom[0])])
            if local_uom:
                res["product_uom_id"] = local_uom.odoo_id.id
        return res

    @mapping
    def product_tmpl_id(self, record):
        res = {}
        if product := record.get("product_tmpl_id"):
            local_product = self.env["odoo.product.template"].search(
                [("external_id", "=", product[0])]
            )
            if local_product:
                res["product_tmpl_id"] = local_product.odoo_id.id
        return res

    @mapping
    def product_id(self, record):
        res = {}
        if product := record.get("product_id"):
            local_product = self.env["odoo.product.product"].search(
                [("external_id", "=", product[0])]
            )
            if local_product:
                res["product_id"] = local_product.odoo_id.id
        return res


class MrpBomImporter(Component):
    _name = "odoo.mrp.bom.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.mrp.bom"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        super()._import_dependencies(force=force)
        record = self.odoo_record
        self._import_dependency(
            record["product_tmpl_id"][0], "odoo.product.template", force=force
        )
        if uom_id := record.get("product_uom_id", False):
            self._import_dependency(uom_id[0], "odoo.uom.uom", force=force)
        if product_id := record.get("product_id", False):
            self._import_dependency(product_id[0], "odoo.product.product", force=force)

    # def _after_import(self, binding, force=False):
    #     """Import the dependencies for the record"""
    #     res = super()._after_import(binding, force=force)
    #     record = self.odoo_record
    #     if bom_lines := record.get("bom_line_ids", False):
    #         for line_id in bom_lines:
    #             self.env["odoo.mrp.bom.line"].with_delay().import_record(
    #                 self.backend_record, line_id, force=force
    #             )
    #     return res
