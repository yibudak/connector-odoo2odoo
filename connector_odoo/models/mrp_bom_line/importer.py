# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class MrpBomLineBatchImporter(Component):
    """Import the BOM Lines."""

    _name = "odoo.mrp.bom.line.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.mrp.bom.line"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for MRP BoM Lines %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


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
        if bom := record.get("bom_id"):
            local_bom = self.env["odoo.mrp.bom"].search(
                [
                    ("external_id", "=", bom[0]),
                    "|",
                    ("active", "=", False),
                    ("active", "=", True),
                ]
            )
            if local_bom:
                res["bom_id"] = local_bom.odoo_id.id
            else:
                raise Exception(
                    "BOM not found, please import it first" f"External ID: {bom[0]}"
                )
        return res

    @mapping
    def product_id(self, record):
        res = {"product_id": False}
        if product := record.get("product_id"):
            local_product = self.binder_for("odoo.product.product").to_internal(
                product[0], unwrap=True
            )
            if local_product:
                res["product_id"] = local_product.id
        return res

    @mapping
    def product_tmpl_id(self, record):
        res = {"product_tmpl_id": False}
        if product := record.get("product_tmpl_id"):
            binder = self.binder_for("odoo.product.template")
            local_product = binder.to_internal(product[0], unwrap=True)
            if local_product:
                res["product_tmpl_id"] = local_product.id
        return res

    @mapping
    def product_uom_id(self, record):
        res = {
            "product_uom_id": False,
        }
        if uom := record.get("product_uom_id"):
            binder = self.binder_for("odoo.uom.uom")
            local_uom = binder.to_internal(uom[0], unwrap=True)
            if local_uom:
                res["product_uom_id"] = local_uom.id
        return res

    @mapping
    def bom_product_template_attribute_value_ids(self, record):
        """
        In Odoo 12 this field is related to bom_id.product_tmpl_id.attribute_line_ids
        and in Odoo 16 this field is related to bom_id.product_tmpl_id.attribute_line_ids.product_template_value_ids
        That's why we need to map it manually.
        """
        res = {"bom_product_template_attribute_value_ids": []}
        attribute_binder = self.binder_for("odoo.product.attribute")
        attribute_value_binder = self.binder_for("odoo.product.attribute.value")
        bom_binder = self.binder_for("odoo.mrp.bom")
        attribute_ids = []
        if attribute_value_ids := record.get("attribute_value_ids"):
            bom_id = bom_binder.to_internal(record["bom_id"][0], unwrap=True)
            for attr_val_id in attribute_value_ids:
                external_attr_val = self.work.odoo_api.browse(
                    model="product.attribute.value", res_id=attr_val_id
                )
                attribute_id = attribute_binder.to_internal(
                    external_attr_val["attribute_id"][0], unwrap=True
                )
                attribute_value_id = attribute_value_binder.to_internal(
                    attr_val_id, unwrap=True
                )
                if not attribute_id or not attribute_value_id:
                    continue
                ptav = self.env["product.template.attribute.value"].search(
                    [
                        ("product_tmpl_id", "=", bom_id.product_tmpl_id.id),
                        ("attribute_id", "=", attribute_id.id),
                        ("product_attribute_value_id", "=", attribute_value_id.id),
                    ],
                    limit=1,
                )
                if ptav:
                    attribute_ids.append(ptav.id)
            res["bom_product_template_attribute_value_ids"] = [(6, 0, attribute_ids)]
        return res


class MrpBomLineImporter(Component):
    _name = "odoo.mrp.bom.line.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.mrp.bom.line"]

    def _get_context(self):
        """
        Do not create procurement for sale order lines.
        """
        ctx = super(MrpBomLineImporter, self)._get_context()
        ctx["skip_cycle_check"] = True
        return ctx

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        super()._import_dependencies(force=force)
        record = self.odoo_record
        # self._import_dependency(record["bom_id"][0], "odoo.mrp.bom", force=force)
        if tmpl_id := record.get("product_tmpl_id"):
            self._import_dependency(tmpl_id[0], "odoo.product.template", force=force)
        if product_id := record.get("product_id"):
            self._import_dependency(product_id[0], "odoo.product.product", force=force)
