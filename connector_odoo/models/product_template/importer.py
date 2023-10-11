# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError
from lxml.html.clean import Cleaner

_logger = logging.getLogger(__name__)


class ProductTemplateBatchImporter(Component):
    """Import the Odoo Products Template.

    For every product category in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.product.template.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.product.template"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo products template %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, force=force)


class ProductTemplateImportMapper(Component):
    _name = "odoo.product.template.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.product.template"]

    direct = [
        ("active", "active"),
        ("description", "description"),
        ("standard_price", "standard_price"),
        ("barcode", "barcode"),
        ("description_purchase", "description_purchase"),
        ("sale_ok", "sale_ok"),
        ("purchase_ok", "purchase_ok"),
        ("type", "detailed_type"),
        ("is_published", "is_published"),
        ("short_public_description", "description_sale"),
        ("website_sequence", "website_sequence"),
        ("qty_increment_step", "qty_increment_step"),
        ("set_product", "set_product"),
        ("sub_component", "sub_component"),
        # ("public_description", "public_description"),
    ]

    @mapping
    def dimensions(self, record):
        binder = self.binder_for("odoo.uom.uom")
        dimensional_uom = binder.to_internal(
            record["dimensional_uom_id"][0], unwrap=True
        )
        weight_uom = binder.to_internal(record["weight_uom_id"][0], unwrap=True)
        volume_uom = binder.to_internal(record["volume_uom_id"][0], unwrap=True)
        return {
            "dimensional_uom_id": dimensional_uom.id,
            "product_length": record["product_length"],
            "product_width": record["product_width"],
            "product_height": record["product_height"],
            "product_weight": record["weight"],
            "weight": record["weight"],
            "product_volume": record["volume"],
            "volume": record["volume"],
            "weight_uom_id": weight_uom.id,
            "volume_uom_id": volume_uom.id,
        }

    @mapping
    def taxes_id(self, record):
        binder = self.binder_for("odoo.account.tax")
        tax_ids = []
        for tax_id in record["taxes_id"]:
            tax = binder.to_internal(tax_id, unwrap=True)
            if tax:
                tax_ids.append(tax.id)
        return {"taxes_id": [(6, 0, tax_ids)]}

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}

    @mapping
    def uom_id(self, record):
        binder = self.binder_for("odoo.uom.uom")
        uom = binder.to_internal(record["uom_id"][0], unwrap=True)
        return {"uom_id": uom.id, "uom_po_id": uom.id}

    # @mapping # Todo: we don't use pricing at template level
    # def price(self, record):
    #     return {"list_price": record.list_price}

    @mapping
    def default_code(self, record):
        # todo: samet
        if not (code := record["default_code"]):
            return {}
        if not code:
            return {"default_code": "/"}
        return {"default_code": code}

    @mapping
    def name(self, record):
        # todo: samet
        if not (name := record["name"]):
            return {}
        if not name:
            return {"name": "/"}
        return {"name": name}

    @mapping
    def category(self, record):
        # todo: samet
        """This method is used to map the category of the product,
        also it will map the public category of the product."""
        vals = {}
        categ_id = record["categ_id"]
        binder = self.binder_for("odoo.product.category")

        cat = binder.to_internal(categ_id[0], unwrap=True)
        if not cat:
            raise MappingError(
                "Can't find external category with odoo_id %s." % categ_id.odoo_id
            )
        vals["categ_id"] = cat.id
        public_category = self.env["product.public.category"].search(
            [("origin_categ_id", "=", cat.id)], limit=1
        )
        if public_category:
            vals["public_categ_ids"] = [(6, 0, [public_category.id])]

        return vals

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
    def public_description(self, record):
        """Sometimes user can edit HTML field with JS editor.
        This may lead to add some old styles from the main instance.
        So we are cleaning the HTML before importing it."""
        vals = {
            "public_description": False,
        }
        if desc := record["public_description"]:
            cleaner = Cleaner(style=True, remove_unknown_tags=False)
            vals["public_description"] = cleaner.clean_html(desc) or ""
        return vals

    # @mapping
    # def default_variant_id(self, record):
    #     vals = {}
    #     if default_variant_id := record.get("default_variant_id"):
    #         binder = self.binder_for("odoo.product.product")
    #         product = binder.to_internal(default_variant_id[0], unwrap=True)
    #         if not product:
    #             raise MappingError(
    #                 "Can't find external product with odoo_id: %s."
    #                 % default_variant_id[0]
    #             )
    #         vals["default_variant_id"] = product.id
    #     return vals


class ProductTemplateImporter(Component):
    _name = "odoo.product.template.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.template"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        # Todo yigit: this causes concurrency issues
        self._import_dependency(
            self.odoo_record["uom_id"][0],
            "odoo.uom.uom",
            force=force,
        )
        self._import_dependency(
            self.odoo_record["categ_id"][0],
            "odoo.product.category",
            force=force,
        )
        # if default_variant_id := self.odoo_record.get("default_variant_id"):
        #     self._import_dependency(
        #         default_variant_id[0],
        #         "odoo.product.product",
        #         force=force,
        #     )

        return super()._import_dependencies(force=force)

    def _get_context(self):
        """Context for the create-write"""
        res = super(ProductTemplateImporter, self)._get_context()
        res["no_handle_variant"] = False
        return res

    def _after_import(self, binding, force=False):
        imported_template = self.binder.to_internal(self.external_id)
        if imported_template:
            self._import_website_attachments(imported_template, force=force)
            self._import_attribute_lines(force=force)
            self._import_feature_lines(force=force)
            self._import_default_variant(imported_template, force=force)
        super(ProductTemplateImporter, self)._after_import(binding, force=force)

    def _import_attribute_lines(self, force=False):
        for attr_line in self.odoo_record["attribute_line_ids"]:
            self.env["odoo.product.template.attribute.line"].delayed_import_record(
                self.backend_record,
                attr_line,
                force=force,
            )
        return True

    def _import_feature_lines(self, force=False):
        for feature_line in self.odoo_record["feature_line_ids"]:
            self.env["odoo.product.template.feature.line"].delayed_import_record(
                self.backend_record,
                feature_line,
                force=force,
            )
        return True

    def _import_website_attachments(self, tmpl_id, force=False):
        if attachment_ids := self.odoo_record["website_attachment_ids"]:
            for attachment_id in attachment_ids:
                self.env["odoo.ir.attachment"].delayed_import_record(
                    self.backend_record, attachment_id, force=force
                )
            imported_attachments = self.env["odoo.ir.attachment"].search(
                [
                    ("external_id", "in", attachment_ids),
                    ("res_model", "=", "product.template"),
                ]
            )
            tmpl_id.write(
                {
                    "website_attachment_ids": [
                        (6, 0, imported_attachments.mapped("odoo_id.id"))
                    ],
                }
            )
        return True

    def _import_default_variant(self, tmpl_id, force=False):
        if default_variant_id := self.odoo_record["default_variant_id"]:
            imported_variant = self.env["odoo.product.product"].search(
                [
                    ("external_id", "=", default_variant_id[0]),
                ],
                limit=1,
            )
            if imported_variant:
                tmpl_id.write(
                    {
                        "default_variant_id": imported_variant.odoo_id.id,
                    }
                )
            else:
                self.env["odoo.product.product"].delayed_import_record(
                    self.backend_record, default_variant_id[0], force=force
                )
        return True

    # We already import images with scheduled actions. No need to import them here.
    # def _import_website_images(self, force):
    #     # Lazy import of images
    #     if image_ids := self.odoo_record["image_ids"]:
    #         for image_id in image_ids:
    #             self.env["odoo.base_multi_image.image"].delayed_import_record(
    #                 self.backend_record, image_id, force=force
    #             )
    #     return True
