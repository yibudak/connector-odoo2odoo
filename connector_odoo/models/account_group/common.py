import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooAccountGroup(models.Model):
    _name = "odoo.account.group"
    _inherit = "odoo.binding"
    _inherits = {"account.group": "odoo_id"}
    _description = "External Odoo Account Account"
    _legacy_import = False
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
            return self.with_delay().import_record(
                self.backend_id, self.external_id, force=True
            )


class AccountGroup(models.Model):
    _inherit = "account.group"

    bind_ids = fields.One2many(
        comodel_name="odoo.account.group",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class AccountGroupAdapter(Component):
    _name = "odoo.account.group.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.account.group"

    _odoo_model = "account.group"


class AccountGroupListener(Component):
    _name = "account.group.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["account.group"]
    _usage = "event.listener"
