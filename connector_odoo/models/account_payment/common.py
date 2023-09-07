# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooAccountPayment(models.Model):
    _name = "odoo.account.payment"
    _inherit = ["odoo.binding"]
    _inherits = {"account.payment": "odoo_id"}
    _description = "Odoo Account Payment"
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


class AccountPayment(models.Model):
    _inherit = "account.payment"

    bind_ids = fields.One2many(
        comodel_name="odoo.account.payment",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class AccountPaymentAdapter(Component):
    _name = "odoo.account.payment.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.account.payment"

    _odoo_model = "account.payment"

    # Set get_passive to True to get the passive records also.
    _get_passive = False
