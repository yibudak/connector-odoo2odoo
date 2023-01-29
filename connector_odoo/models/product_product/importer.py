# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class ProductBatchImporter(Component):
    """Import the Odoo Products.

    For every product category in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.product.product.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.product.product"]

    def run(self, filters=None, force=False):
        """Run the synchronization"""
        external_ids = self.backend_adapter.search(filters)
        _logger.debug(
            "search for odoo products %s returned %s items", filters, len(external_ids)
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options, force=force)


class ProductImportMapper(Component):
    _name = "odoo.product.product.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.product.product"]

    direct = [
        ("is_published", "is_published"),
        ("description", "description"),
        ("standard_price", "standard_price"),
        ("description_sale", "description_sale"),
        ("description_purchase", "description_purchase"),
        ("description_sale", "description_sale"),
        ("sale_ok", "sale_ok"),
        ("purchase_ok", "purchase_ok"),
        ("type", "detailed_type"),
        ("public_description", "public_description"),
        # ("v_cari_urun", "v_cari_urun"),
    ]

    @mapping
    def template_and_attributes(self, record):
        attr_line_vals = []
        tmpl_binder = self.binder_for("odoo.product.template")
        attr_value_binder = self.binder_for("odoo.product.attribute.value")
        local_template_id = tmpl_binder.to_internal(
            record.product_tmpl_id.id, unwrap=True
        )
        attr_value_ids = record.attribute_value_ids
        for attr_value in attr_value_ids:
            local_attr_val_id = attr_value_binder.to_internal(
                attr_value.id, unwrap=True
            )

            if not local_attr_val_id:
                raise MappingError(
                    "Attribute not found for value %s."
                    " Import attributes first" % attr_value.name
                )
            attribute = self.env["product.template.attribute.value"].search(
                [
                    ("product_tmpl_id", "=", local_template_id.id),
                    ("attribute_id", "=", local_attr_val_id.attribute_id.id),
                    ("product_attribute_value_id", "=", local_attr_val_id.id),
                ]
            )
            if attribute:
                attr_line_vals.append(attribute.id)

        return {
            "product_tmpl_id": local_template_id.id,
            "product_template_attribute_value_ids": [(6, 0, attr_line_vals)],
        }

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}

    @mapping
    def uom_id(self, record):
        binder = self.binder_for("odoo.uom.uom")
        uom = binder.to_internal(record.uom_id.id, unwrap=True)
        return {"uom_id": uom.id, "uom_po_id": uom.id}

    @mapping
    def dimensions(self, record):
        binder = self.binder_for("odoo.uom.uom")
        uom = binder.to_internal(record.dimensional_uom_id.id, unwrap=True)
        return {
            "dimensional_uom_id": uom.id,
            "product_length": record.product_length,
            "product_width": record.product_width,
            "product_height": record.product_height,
            "weight": record.weight,
        }
        # Todo: weight'in uomu eksik, v16'da m2o yerine char yapmışlar

    @mapping
    def price(self, record):
        return {"sale_price": record.attr_price}

    @mapping
    def default_code(self, record):
        code = record.default_code
        if not code:
            return {"default_code": "/"}
        return {"default_code": code}

    @mapping
    def name(self, record):
        if not hasattr(record, "name"):
            return {}
        name = record.name
        if not name:
            return {"name": "/"}
        return {"name": name}

    @mapping
    def category(self, record):
        categ_id = record.categ_id
        binder = self.binder_for("odoo.product.category")

        cat = binder.to_internal(categ_id.id, unwrap=True)
        if not cat:
            raise MappingError(
                "Can't find external category with odoo_id %s." % categ_id.id
            )
        return {"categ_id": cat.id}

    @mapping
    def is_published(self, record):
        return {
            "is_published": True
        }

    @mapping
    def image(self, record):
        if self.backend_record.version in (
            "10.0",
            "11.0",
            "12.0",
        ):
            return {"image_1920": record.image_medium if hasattr(record, "image_medium") else False}
        else:
            return {"image_1920": record.image_1920}

    @mapping
    def barcode(self, record):
        barcode = False
        if hasattr(record, "barcode"):
            barcode = record["barcode"]
        elif hasattr(record, "ean13"):
            barcode = record["ean13"]
        return {"barcode": barcode}


class ProductImporter(Component):
    _name = "odoo.product.product.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.product"]

    def _import_dependencies(self, force=False):
        if self.backend_record.work_with_variants:
            product_tmpl_id = self.odoo_record.product_tmpl_id
            tmpl_binder = self.binder_for("odoo.product.template")
            odoo_product_tmpl_id = tmpl_binder.to_internal(
                product_tmpl_id.id, unwrap=True
            )

            if not odoo_product_tmpl_id:
                self._import_dependency(
                    product_tmpl_id.id, "odoo.product.template", force=force
                )

        return super()._import_dependencies(force=force)

    def _after_import(self, binding, force=False):
        # attachment_model = self.work.odoo_api.api.env["ir.attachment"]
        # attachment_ids = attachment_model.search(
        #     [
        #         ("res_model", "=", "product.product"),
        #         ("res_id", "=", self.odoo_record.id),
        #     ],
        #     order="id",
        # )
        # total = len(attachment_ids)
        # _logger.debug(
        #     "{} Attachment found for external product {}".format(
        #         total, self.odoo_record.id
        #     )
        # )
        # for attachment_id in attachment_ids:
        #     self.env["odoo.ir.attachment"].with_delay().import_record(
        #         self.backend_record, attachment_id
        #     )
        return super()._after_import(binding, force)
