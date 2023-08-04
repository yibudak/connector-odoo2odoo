# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooDeliveryCarrier(models.Model):
    _name = "odoo.delivery.carrier"
    _inherit = "odoo.binding"
    _inherits = {"delivery.carrier": "odoo_id"}
    _description = "External Odoo Delivery Carrier"
    _sql_constraints = [
        (
            "external_id",
            "UNIQUE(external_id)",
            "External ID (external_id) must be unique!",
        ),
    ]

    def name_get(self):
        result = []
        for op in self:
            name = "{} (Backend: {})".format(
                op.odoo_id.display_name, op.backend_id.display_name
            )
            result.append((op.id, name))

        return result

    def resync(self):
        if self.backend_id.main_record == "odoo":
            return self.with_delay().export_record(self.backend_id)
        else:
            return self.with_delay().import_record(
                self.backend_id, self.external_id, force=True
            )


class DeliveryCarrier(models.Model):
    _inherit = "delivery.carrier"

    bind_ids = fields.One2many(
        comodel_name="odoo.delivery.carrier",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class DeliveryCarrierAdapter(Component):
    _name = "odoo.delivery.carrier.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.delivery.carrier"

    _odoo_model = "delivery.carrier"

    # Set get_passive to True to get the passive records also.
    _get_passive = True

    def search(self, domain=None, model=None, offset=0, limit=None, order=None):
        """Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        if domain is None:
            domain = []
        return super(DeliveryCarrierAdapter, self).search(
            domain=domain, model=model, offset=offset, limit=limit, order=order
        )


class DeliveryCarrierListener(Component):
    _name = "delivery.carrier.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["delivery.carrier"]
    _usage = "event.listener"
