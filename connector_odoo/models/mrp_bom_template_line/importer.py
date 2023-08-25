# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError


_logger = logging.getLogger(__name__)


class MrpBomTemplateLineBatchImporter(Component):
    """Import the BOM Lines."""

    _name = "odoo.mrp.bom.template.line.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.mrp.bom.template.line"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""
        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for MRP BoM Template line %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options, force=force)


class MrpBomTemplateLineMapper(Component):
    _name = "odoo.mrp.bom.template.line.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.mrp.bom.template.line"]

    direct = [
        ("sequence", "sequence"),
        ("product_qty", "product_qty"),
    ]

    @mapping
    def bom_id(self, record):
        res = {
            "bom_id": False,
        }
        if bom := record.get("bom_id"):
            local_bom = self.env["odoo.mrp.bom"].search([("external_id", "=", bom[0])])
            if local_bom:
                res["bom_id"] = local_bom.odoo_id.id
        return res

    @mapping
    def product_tmpl_id(self, record):
        res = {
            "product_tmpl_id": False,
        }
        if product := record.get("product_tmpl_id"):
            local_product = self.env["odoo.product.template"].search(
                [("external_id", "=", product[0])]
            )
            if local_product:
                res["product_tmpl_id"] = local_product.odoo_id.id
        return res

    @mapping
    def product_uom_id(self, record):
        res = {"product_uom_id": False}
        if uom := record.get("product_uom_id"):
            local_uom = self.env["odoo.uom.uom"].search([("external_id", "=", uom[0])])
            if local_uom:
                res["product_uom_id"] = local_uom.odoo_id.id
        return res

    @mapping
    def attributes(self, record):
        """
        Odoo 12 -> Odoo 16
        attribute_value_ids -> bom_product_template_attribute_value_ids
        target_attribute_value_ids -> target_bom_product_template_attribute_value_ids
        inherited_attribute_ids -> inherited_attribute_ids
        """
        res = {}
        attribute_binder = self.binder_for("odoo.product.attribute")
        attribute_value_binder = self.binder_for("odoo.product.attribute.value")
        bom_binder = self.binder_for("odoo.mrp.bom")
        local_bom_id = bom_binder.to_internal(record["bom_id"][0], unwrap=True)
        if attribute_value_ids := record["attribute_value_ids"]:
            val_ids = []
            for attr_val in attribute_value_ids:
                local_attr_val = attribute_value_binder.to_internal(
                    attr_val, unwrap=True
                )
                if not local_attr_val:
                    raise MappingError(
                        f"Product Attribute Value with external id"
                        f" {attr_val} not found."
                    )
                mapped_attr_val = self.env["product.template.attribute.value"].search(
                    [
                        ("product_tmpl_id", "=", local_bom_id.product_tmpl_id.id),
                        ("product_attribute_value_id", "=", local_attr_val.id),
                    ]
                )
                if mapped_attr_val:
                    val_ids.append(mapped_attr_val.id)
            res["bom_product_template_attribute_value_ids"] = [(6, 0, val_ids)]
        if target_attribute_value_ids := record["target_attribute_value_ids"]:
            val_ids = []
            for attr_val in target_attribute_value_ids:
                local_attr_val = attribute_value_binder.to_internal(
                    attr_val, unwrap=True
                )
                if not local_attr_val:
                    raise MappingError(
                        f"Product Attribute Value with external id"
                        f" {attr_val} not found."
                    )
                mapped_attr_val = self.env["product.template.attribute.value"].search(
                    [
                        ("product_tmpl_id", "=", local_bom_id.product_tmpl_id.id),
                        ("product_attribute_value_id", "=", local_attr_val.id),
                    ]
                )
                if mapped_attr_val:
                    val_ids.append(mapped_attr_val.id)
            res["target_bom_product_template_attribute_value_ids"] = [(6, 0, val_ids)]
        if inherited_attribute_ids := record["inherited_attribute_ids"]:
            attr_ids = []
            for attr in inherited_attribute_ids:
                local_attr = attribute_binder.to_internal(attr, unwrap=True)
                if not local_attr:
                    raise MappingError(
                        f"Product Attribute with external id {attr} not found."
                    )
                attr_ids.append(local_attr.id)
            res["inherited_attribute_ids"] = [(6, 0, attr_ids)]
        return res


class MrpBomTemplateLineImporter(Component):
    _name = "odoo.mrp.bom.template.line.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.mrp.bom.template.line"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        super()._import_dependencies(force=force)
        record = self.odoo_record
        # self._import_dependency(
        #     record.bom_id.id, "odoo.mrp.bom", force=force
        # )
        if tmpl_id := record.get("product_tmpl_id"):
            self._import_dependency(tmpl_id[0], "odoo.product.template", force=force)
