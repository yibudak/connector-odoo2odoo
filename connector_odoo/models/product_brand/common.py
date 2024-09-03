# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooProductBrand(models.Model):
    _queue_priority = 5
    _name = "odoo.product.brand"
    _inherit = "odoo.binding"
    _inherits = {"product.brand": "odoo_id"}
    _description = "Odoo Product Brand"
    _sql_constraints = [
        (
            "external_id",
            "UNIQUE(external_id)",
            "External ID (external_id) must be unique!",
        ),
    ]

    def resync(self):
        self.delayed_import_record(self.backend_id, self.external_id, force=True)


class ProductModel(models.Model):
    _inherit = "product.brand"

    bind_ids = fields.One2many(
        comodel_name="odoo.product.brand",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class ProductModelAdapter(Component):
    _name = "odoo.product.brand.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.product.brand"

    _odoo_model = "product.brand"

    # Set get_passive to True to get the passive records also.
    _get_passive = False
