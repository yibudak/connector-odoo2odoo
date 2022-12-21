# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import logging
from odoo import fields, models
from odoo.addons.component.core import Component
_logger = logging.getLogger(__name__)


# https://github.com/odoo-turkey/l10n-turkey

class OdooAddressNeighbour(models.Model):
    _name = "odoo.address.neighbour"
    _inherit = "odoo.binding"
    _inherits = {"address.neighbour": "odoo_id"}
    _description = "External Odoo Address Neighbour"

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

    def create(self, vals):
        return super().create(vals)


class AddressNeighbour(models.Model):
    _inherit = "address.neighbour"

    bind_ids = fields.One2many(
        comodel_name="odoo.ir.attachment",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class IrAttachmentAdapter(Component):
    _name = "odoo.address.neighbour"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.address.neighbour"

    _odoo_model = "address.neighbour"

