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
            self._import_record(external_id, force=force)


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
            binder = self.binder_for("odoo.mrp.bom")
            local_bom = binder.to_internal(bom[0], unwrap=True)
            if local_bom:
                res["bom_id"] = local_bom.id
        return res

    @mapping
    def product_tmpl_id(self, record):
        res = {}
        if product := record["product_tmpl_id"]:
            binder = self.binder_for("odoo.product.template")
            local_product = binder.to_internal(product[0], unwrap=True)
            if local_product:
                res.update({"product_tmpl_id": local_product.id})
        return res

    @mapping
    def product_uom_id(self, record):
        res = {}
        if uom := record.get("product_uom_id"):
            binder = self.binder_for("odoo.uom.uom")
            local_uom = binder.to_internal(uom[0], unwrap=True)
            if local_uom:
                res.update({"product_uom_id": local_uom.id})
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
                val_ids.append(local_attr_val.id)
            res["attribute_value_ids"] = [(6, 0, val_ids)]
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
                val_ids.append(local_attr_val.id)
            res["target_attribute_value_ids"] = [(6, 0, val_ids)]
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
