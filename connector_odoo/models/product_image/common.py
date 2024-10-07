import logging
from odoo import fields, models
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooProductImage(models.Model):
    """
    Actually we are using base_multi_image_image model for product images on version 12.0
    This is a temporary solution for version 16.0. Kinda tricky.

    base_multi_image.image ->>> product.image

    """

    _queue_priority = 15
    _name = "odoo.product.image"
    _inherit = "odoo.binding"
    _inherits = {"product.image": "odoo_id"}
    _description = "External Odoo Product Images"
    _sql_constraints = [
        (
            "external_id",
            "UNIQUE(external_id)",
            "External ID (external_id) must be unique!",
        ),
    ]

    def resync(self):
        if self.backend_id.main_record == "odoo":
            return self.delayed_export_record(self.backend_id)
        else:
            return self.delayed_import_record(
                self.backend_id, self.external_id, force=True
            )

    def create(self, vals):
        return super().create(vals)


class ProductImage(models.Model):
    _inherit = "product.image"

    bind_ids = fields.One2many(
        comodel_name="odoo.product.image",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class ProductImageAdapter(Component):
    _name = "odoo.product.image.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.product.image"

    _odoo_model = "product.image"

    # Set get_passive to True to get the passive records also.
    _get_passive = False


class ProductImageListener(Component):
    _name = "product.image.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["product.image"]
    _usage = "event.listener"
