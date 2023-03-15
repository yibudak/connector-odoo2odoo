import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooAddressNeighbour(models.Model):
    _name = "odoo.address.neighbour"
    _inherit = "odoo.binding"
    _inherits = {"address.neighbour": "odoo_id"}
    _description = "External Odoo Address District"
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


class AddressNeighbour(models.Model):
    _inherit = "address.neighbour"

    bind_ids = fields.One2many(
        comodel_name="odoo.address.neighbour",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class AddressNeighbourAdapter(Component):
    _name = "odoo.address.neighbour.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.address.neighbour"

    _odoo_model = "address.neighbour"


class AddressNeighbourListener(Component):
    _name = "address.neighbour.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["address.neighbour"]
    _usage = "event.listener"
