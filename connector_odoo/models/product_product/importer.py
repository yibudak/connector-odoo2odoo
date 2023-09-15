# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


def _compute_attribute_line_vals(importer, record):
    ptav_list = importer.env["product.template.attribute.value"]
    tmpl_binder = importer.binder_for("odoo.product.template")
    attr_value_binder = importer.binder_for("odoo.product.attribute.value")
    local_template_id = tmpl_binder.to_internal(
        record["product_tmpl_id"][0], unwrap=True
    )

    if not local_template_id:
        return local_template_id, []

    for attr_value_id in record["attribute_value_ids"]:
        local_attr_val_id = attr_value_binder.to_internal(attr_value_id, unwrap=True)

        if not local_attr_val_id:
            raise MappingError(
                "Attribute not found for value %s."
                " Import attributes first" % attr_value_id
            )
        ptav = importer.env["product.template.attribute.value"].search(
            [
                ("product_tmpl_id", "=", local_template_id.id),
                ("attribute_id", "=", local_attr_val_id.attribute_id.id),
                ("product_attribute_value_id", "=", local_attr_val_id.id),
                ("ptav_active", "=", True),
            ],
            limit=1,
        )
        if ptav:
            ptav_list |= ptav
    return local_template_id, ptav_list


class ProductBatchImporter(Component):
    """Import the Odoo Products.

    For every product category in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.product.product.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.product.product"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""
        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo products %s returned %s items", domain, len(external_ids)
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class ProductImportMapper(Component):
    _name = "odoo.product.product.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.product.product"]

    direct = [
        ("active", "active"),
        ("is_published", "is_published"),
        ("description", "description"),
        ("standard_price", "standard_price"),
        ("description_sale", "description_sale"),
        ("description_purchase", "description_purchase"),
        ("description_sale", "description_sale"),
        ("sale_ok", "sale_ok"),
        ("purchase_ok", "purchase_ok"),
        ("type", "detailed_type"),
        ("is_published", "is_published"),
        ("public_description", "public_description"),
    ]

    @mapping
    def template_and_attributes(self, record):
        """Map template and attributes"""
        tmpl_id, ptav_list = _compute_attribute_line_vals(importer=self, record=record)

        if not (tmpl_id and ptav_list):
            return {}

        combination_indices = ptav_list._ids2str()

        vals = {
            "product_tmpl_id": tmpl_id.id,
            "product_template_attribute_value_ids": [(6, 0, ptav_list.ids)],
            "combination_indices": combination_indices,
        }

        if vals["combination_indices"] == "":
            vals.pop("combination_indices")

        exist_product = self.env["product.product"].search(
            [
                ("product_tmpl_id", "=", tmpl_id.id),
                (
                    "combination_indices",
                    "=",
                    combination_indices,
                ),
            ]
        )
        if exist_product:
            vals["odoo_id"] = exist_product.id

        return vals

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}

    @mapping
    def uom_id(self, record):
        binder = self.binder_for("odoo.uom.uom")
        uom = binder.to_internal(record["uom_id"][0], unwrap=True)
        return {"uom_id": uom.id, "uom_po_id": uom.id}

    @mapping
    def v_cari_urun(self, record):
        vals = {
            "v_cari_urun": False,
        }
        if v_cari_urun := record["v_cari_urun"]:
            binder = self.binder_for("odoo.res.partner")
            partner = binder.to_internal(v_cari_urun[0], unwrap=True)
            vals.update({"v_cari_urun": partner.id})
        return vals

    @mapping
    def dimensions(self, record):
        binder = self.binder_for("odoo.uom.uom")
        uom = binder.to_internal(record["dimensional_uom_id"][0], unwrap=True)
        return {
            "dimensional_uom_id": uom.id,
            "product_length": record["product_length"],
            "product_width": record["product_width"],
            "product_height": record["product_height"],
            "weight": record["weight"],
            "volume": record["volume"],
        }
        # Todo: volume ve weight'in uomu eksik, v16'da m2o yerine char yapmışlar

    @mapping
    def price(self, record):
        return {"sale_price": record.get("attr_price", 0.0)}

    @mapping
    def default_code(self, record):
        return {"default_code": record.get("default_code", "/")}

    @mapping
    def name(self, record):
        return {"name": record.get("name", "/")}

    @mapping
    def category(self, record):
        categ_id = record["categ_id"]
        binder = self.binder_for("odoo.product.category")
        cat = binder.to_internal(categ_id[0], unwrap=True)
        if not cat:
            raise MappingError(
                "Can't find external category with odoo_id %s." % categ_id.id
            )
        return {"categ_id": cat.id}

    @mapping
    def image(self, record):
        if self.backend_record.version in (
            "6.1",
            "7.0",
            "8.0",
            "9.0",
            "10.0",
            "11.0",
            "12.0",
        ):
            return {"image_1920": record["image_main"]}
        else:
            return {"image_1920": record["image_1920"]}

    @mapping
    def barcode(self, record):
        barcode = record.get("barcode") or record.get("ean13")
        return {"barcode": barcode}


class ProductImporter(Component):
    _name = "odoo.product.product.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.product"]

    def _must_skip(self):
        """If the product is not active and won't be active, we skip it"""
        binding = self.model.search(
            [
                ("backend_id", "=", self.backend_record.id),
                ("external_id", "=", self.external_id),
                "|",
                ("active", "=", True),
                ("active", "=", False),
            ],
            limit=1,
        )
        if (binding and not binding.active) and not self.odoo_record.get("active"):
            return True
        return super()._must_skip()

    def _get_binding_with_data(self, binding):
        """Match the attachment with hashed store_fname."""
        binding = super(ProductImporter, self)._get_binding_with_data(binding)
        if not binding:
            tmpl_id, ptav_list = _compute_attribute_line_vals(
                importer=self, record=self.odoo_record
            )
            if ptav_list and tmpl_id:
                binding = self.model.search(
                    [
                        ("product_tmpl_id", "=", tmpl_id.id),
                        ("combination_indices", "=", ptav_list._ids2str()),
                    ],
                    limit=1,
                )
        return binding

    def _import_dependencies(self, force=False):
        self._import_dependency(
            self.odoo_record["product_tmpl_id"][0], "odoo.product.template", force=force
        )

        if self.odoo_record["v_cari_urun"]:
            partner_id = self.odoo_record["v_cari_urun"][0]
            self._import_dependency(partner_id, "odoo.res.partner", force=force)

        if attr_vals := self.odoo_record["attribute_value_ids"]:
            for attr_val_id in attr_vals:
                self._import_dependency(
                    attr_val_id, "odoo.product.attribute.value", force=force
                )

        return super()._import_dependencies(force=force)
