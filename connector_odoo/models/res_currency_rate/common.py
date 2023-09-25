# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooResCurrencyRate(models.Model):
    _queue_priority = 5
    _name = "odoo.res.currency.rate"
    _inherit = ["odoo.binding"]
    _inherits = {"res.currency.rate": "odoo_id"}
    _description = "Odoo Currency rate"
    _sql_constraints = [
        (
            "external_id",
            "UNIQUE(external_id)",
            "External ID (external_id) must be unique!",
        ),
    ]

    def resync(self):
        if self.backend_id.main_record == "odoo":
            raise NotImplementedError
        else:
            return self.delayed_import_record(
                self.backend_id, self.external_id, force=True
            )


class ResCurrencyRate(models.Model):
    _inherit = "res.currency.rate"

    bind_ids = fields.One2many(
        comodel_name="odoo.res.currency.rate",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class ResCurrencyRateAdapter(Component):
    _name = "odoo.res.currency.rate.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.res.currency.rate"

    _odoo_model = "res.currency.rate"

    # Set get_passive to True to get the passive records also.
    _get_passive = False
