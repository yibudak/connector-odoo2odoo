# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooProductPricelist(models.Model):
    _name = "odoo.product.pricelist"
    _inherit = "odoo.binding"
    _inherits = {"product.pricelist": "odoo_id"}
    _description = "Odoo Product Pricelist"
    _sql_constraints = [
        (
            "external_id",
            "UNIQUE(external_id)",
            "External ID (external_id) must be unique!",
        ),
    ]

    def resync(self):
        if self.backend_id.main_record == "odoo":
            return self.with_delay().export_record(self.backend_id)
        else:
            return self.delayed_import_record(
                self.backend_id, self.external_id, force=True
            )


class ProductPricelist(models.Model):
    _inherit = "product.pricelist"

    bind_ids = fields.One2many(
        comodel_name="odoo.product.pricelist",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class ProductPricelistAdapter(Component):
    _name = "odoo.product.pricelist.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.product.pricelist"

    _odoo_model = "product.pricelist"

    # Set get_passive to True to get the passive records also.
    _get_passive = True


class OdooProductPricelistItem(models.Model):
    _name = "odoo.product.pricelist.item"
    _inherit = "odoo.binding"
    _inherits = {"product.pricelist.item": "odoo_id"}
    _description = "Odoo Product Pricelist Item"

    def resync(self):
        if self.backend_id.main_record == "odoo":
            return self.with_delay().export_record(self.backend_id)
        else:
            return self.delayed_import_record(
                self.backend_id, self.external_id, force=True
            )


class ProductPricelistItem(models.Model):
    _inherit = "product.pricelist.item"

    bind_ids = fields.One2many(
        comodel_name="odoo.product.pricelist.item",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class ProductPricelistItemAdapter(Component):
    _name = "odoo.product.pricelist.item.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.product.pricelist.item"

    _odoo_model = "product.pricelist.item"

    # Set get_passive to True to get the passive records also.
    _get_passive = False

    def search(self, domain=None, model=None, offset=0, limit=None, order=None):
        """Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        if domain is None:
            domain = []

        return super(ProductPricelistItemAdapter, self).search(
            domain=domain, model=model, offset=offset, limit=limit, order=order
        )
