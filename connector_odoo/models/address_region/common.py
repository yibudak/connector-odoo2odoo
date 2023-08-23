import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooAddressRegion(models.Model):
    _name = "odoo.address.region"
    _inherit = "odoo.binding"
    _inherits = {"address.region": "odoo_id"}
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
            return self.delayed_import_record(
                self.backend_id, self.external_id, force=True
            )


class AddressRegion(models.Model):
    _inherit = "address.region"

    bind_ids = fields.One2many(
        comodel_name="odoo.address.region",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class AddressRegionAdapter(Component):
    _name = "odoo.address.region.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.address.region"

    _odoo_model = "address.region"

    # Set get_passive to True to get the passive records also.
    _get_passive = False


class AddressRegionListener(Component):
    _name = "address.region.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["address.region"]
    _usage = "event.listener"
