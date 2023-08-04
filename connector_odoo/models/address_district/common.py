import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooAddressDistrict(models.Model):
    _name = "odoo.address.district"
    _inherit = "odoo.binding"
    _inherits = {"address.district": "odoo_id"}
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


class AddressDistrict(models.Model):
    _inherit = "address.district"

    bind_ids = fields.One2many(
        comodel_name="odoo.address.district",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class AddressDistrictAdapter(Component):
    _name = "odoo.address.district.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.address.district"

    _odoo_model = "address.district"

    # Set get_passive to True to get the passive records also.
    _get_passive = False


class AddressDistrictListener(Component):
    _name = "address.district.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["address.district"]
    _usage = "event.listener"
