import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooAccountPaymentTerm(models.Model):
    _queue_priority = 5
    _name = "odoo.account.payment.term"
    _inherit = "odoo.binding"
    _inherits = {"account.payment.term": "odoo_id"}
    _description = "External Odoo Account Account"
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


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"

    bind_ids = fields.One2many(
        comodel_name="odoo.account.payment.term",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class AccountPaymentTermAdapter(Component):
    _name = "odoo.account.payment.term.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.account.payment.term"

    _odoo_model = "account.payment.term"

    # Set get_passive to True to get the passive records also.
    _get_passive = True


class AccountPaymentTermListener(Component):
    _name = "account.payment.term.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["account.payment.term"]
    _usage = "event.listener"
