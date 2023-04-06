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

    def run(self, filters=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(filters)
        _logger.info(
            "search for odoo products template %s returned %s items",
            filters,
            len(external_ids),
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options, force=force)


class ProductTemplateImportMapper(Component):
    _name = "odoo.product.template.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.product.template"]

    direct = [
        ("description", "description"),
        ("weight", "weight"),
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
        # ("public_description", "public_description"),
    ]

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}

    @mapping
    def uom_id(self, record):
        binder = self.binder_for("odoo.uom.uom")
        uom = binder.to_internal(record.uom_id.id, unwrap=True)
        return {"uom_id": uom.id, "uom_po_id": uom.id}

    # @mapping # Todo: we don't use pricing at template level
    # def price(self, record):
    #     return {"list_price": record.list_price}

    @mapping
    def default_code(self, record):
        if not hasattr(record, "default_code"):
            return {}
        code = record["default_code"]
        if not code:
            return {"default_code": "/"}
        return {"default_code": code}

    @mapping
    def name(self, record):
        if not hasattr(record, "name"):
            return {}
        name = record["name"]
        if not name:
            return {"name": "/"}
        return {"name": name}

    @mapping
    def category(self, record):
        """This method is used to map the category of the product,
        also it will map the public category of the product."""
        vals = {}
        categ_id = record["categ_id"]
        binder = self.binder_for("odoo.product.category")

        cat = binder.to_internal(categ_id.id, unwrap=True)
        if not cat:
            raise MappingError(
                "Can't find external category with odoo_id %s." % categ_id.odoo_id
            )
        vals["categ_id"] = cat.id
        public_category = self.env["product.public.category"].search(
            [("origin_categ_id", "=", cat.id)], limit=1
        )
        if public_category:
            vals["public_categ_ids"] = [(4, public_category.id)]

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
            return {
                "image_1920": record.image_medium
                if hasattr(record, "image_medium")
                else False
            }
        else:
            return {"image_1920": record.image_1920}

    @mapping
    def public_description(self, record):
        """Sometimes user can edit HTML field with JS editor.
        This may lead to add some old styles from the main instance.
        So we are cleaning the HTML before importing it."""
        vals = {}
        if record.public_description:
            cleaner = Cleaner(style=True, remove_unknown_tags=False)
            vals["public_description"] = (
                cleaner.clean_html(record.public_description) or ""
            )
        return vals


class ProductTemplateImporter(Component):
    _name = "odoo.product.template.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.template"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        # Todo yigit: this causes concurrency issues
        uom_id = self.odoo_record.uom_id
        self._import_dependency(uom_id.id, "odoo.uom.uom", force=force)

        categ_id = self.odoo_record.categ_id
        self._import_dependency(categ_id.id, "odoo.product.category", force=force)

        return super()._import_dependencies(force=force)

    def _get_context(self, data):
        """Context for the create-write"""
        res = super(ProductTemplateImporter, self)._get_context(data)
        res["no_handle_variant"] = False
        return res

    def _after_import(self, binding, force=False):
        imported_template = self.binder.to_internal(self.external_id)
        if imported_template:
            self._import_website_images(force=force)
            self._import_website_attachments(imported_template, force=force)
            self._import_attribute_lines(force=force)
            self._import_feature_lines(force=force)
        super(ProductTemplateImporter, self)._after_import(binding, force=force)

    def _import_attribute_lines(self, force=False):
        for attr_line in self.odoo_record.attribute_line_ids:
            self.env["odoo.product.template.attribute.line"].import_record(
                self.backend_record,
                attr_line.id,
                force=force,
            )
        return True

    def _import_feature_lines(self, force=False):
        for feature_line in self.odoo_record.feature_line_ids:
            self.env["odoo.product.template.feature.line"].import_record(
                self.backend_record,
                feature_line.id,
                force=force,
            )
        return True

    def _import_website_attachments(self, tmpl_id, force=False):
        attachment_ids = self.odoo_record.website_attachment_ids
        if attachment_ids:
            for attachment_id in attachment_ids:
                self.env["odoo.ir.attachment"].with_delay().import_record(
                    self.backend_record, attachment_id.id, force=force
                )
            imported_attachments = self.env["ir.attachment"].search(
                [
                    ("bind_ids.external_id", "in", attachment_ids.ids),
                    ("res_model", "=", "product.template"),
                ]
            )
            tmpl_id.write(
                {
                    "website_attachment_ids": [(6, 0, imported_attachments.ids)],
                }
            )
        return True

    def _import_website_images(self, force):
        image_ids = self.odoo_record.image_ids
        if image_ids:
            for image_id in image_ids:
                self.env["odoo.product.image"].with_delay().import_record(
                    self.backend_record, image_id.id, force=force
                )
        return True
