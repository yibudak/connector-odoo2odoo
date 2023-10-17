import logging
from odoo import fields, models, api
from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooBaseMultiImageImage(models.Model):
    """
    This is the real mapping model for product images on version 16.0
    You can avoid product.image model and use this model instead.
    """

    _queue_priority = 15
    _name = "odoo.base_multi_image.image"
    _inherit = "odoo.binding"
    _inherits = {"base_multi_image.image": "odoo_id"}
    _description = "External Odoo Base Multi Images"
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


class BaseMultiImageImage(models.Model):
    _inherit = "base_multi_image.image"

    bind_ids = fields.One2many(
        comodel_name="odoo.base_multi_image.image",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )

    # We have a bug when we try to import images from Odoo to Odoo
    # So we need to override this method and remove the check
    @api.constrains("storage", "file_db_store")
    def _check_store(self):
        return True


class BaseMultiImageImageAdapter(Component):
    _name = "odoo.base_multi_image.image.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.base_multi_image.image"

    _odoo_model = "base_multi_image.image"

    # Set get_passive to True to get the passive records also.
    _get_passive = False


class ProductImageListener(Component):
    _name = "base_multi_image.image.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["base_multi_image.image"]
    _usage = "event.listener"
