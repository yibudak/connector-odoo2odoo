# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import logging

from odoo import api, fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooProductTemplate(models.Model):
    _name = "odoo.product.template"
    _inherit = "odoo.binding"
    _inherits = {"product.template": "odoo_id"}
    _description = "External Odoo Product Template"
    _sql_constraints = [
        (
            "external_id",
            "UNIQUE(external_id)",
            "External ID (external_id) must be unique!",
        ),
    ]

    def name_get(self):
        result = []
        for op in self:
            name = "{} (Backend: {})".format(
                op.odoo_id.display_name,
                op.backend_id.display_name,
            )
            result.append((op.id, name))

        return result

    RECOMPUTE_QTY_STEP = 1000  # products at a time

    def export_inventory(self, fields=None):
        """Export the inventory configuration and quantity of a product."""
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage="product.inventory.exporter")
            return exporter.run(self, fields)

    def resync(self):
        return self.with_delay().import_record(
            self.backend_id, self.external_id, force=True
        )


class ProductTemplate(models.Model):
    _inherit = "product.template"

    bind_ids = fields.One2many(
        comodel_name="odoo.product.template",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )

    product_bind_ids = fields.Many2many(
        comodel_name="odoo.product.product",
        compute="_compute_product_bind_ids",
        store=True,
    )

    def _create_variant_ids(self):
        """We are handling variants with Odoo 12.0"""
        return True
        # if self.env.context.get("no_handle_variant", False):
        #     return True
        # else:
        #     res = super(ProductTemplate, self)._create_variant_ids()

    @api.depends("product_variant_ids")
    def _compute_product_bind_ids(self):
        for record in self:
            record.product_bind_ids = record.product_variant_ids.mapped("bind_ids")

    def multi_fix_product_images(self):
        """This method fixes main image of the all the products."""
        for product in self.search([]):
            variant_img = fields.first(product.product_template_image_ids)
            if variant_img:
                product.write(
                    {
                        "image_1920": variant_img.image_1920,
                        "image_1024": variant_img.image_1024,
                        "image_512": variant_img.image_512,
                    }
                )
                product._compute_can_image_1024_be_zoomed()
        return True


class ProductTemplateAdapter(Component):
    _name = "odoo.product.template.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.product.template"

    _odoo_model = "product.template"

    def search(self, filters=None, model=None, offset=0, limit=None, order=None):
        """Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        if filters is None:
            filters = []
        ext_filter = ast.literal_eval(
            str(self.backend_record.external_product_template_domain_filter)
        )
        filters += ext_filter
        return super(ProductTemplateAdapter, self).search(
            filters=filters, model=model, offset=offset, limit=limit, order=order
        )
