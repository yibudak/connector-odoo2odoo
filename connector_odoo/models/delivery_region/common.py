# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooDeliveryRegion(models.Model):
    _name = "odoo.delivery.region"
    _inherit = "odoo.binding"
    _inherits = {"delivery.region": "odoo_id"}
    _description = "External Odoo Delivery Region"
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


class DeliveryRegion(models.Model):
    _inherit = "delivery.region"

    bind_ids = fields.One2many(
        comodel_name="odoo.delivery.region",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class DeliveryRegionAdapter(Component):
    _name = "odoo.delivery.region.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.delivery.region"

    _odoo_model = "delivery.region"

    # def search(self, domain=None, model=None, offset=0, limit=None, order=None):
    #     """Search records according to some criteria
    #     and returns a list of ids
    #
    #     :rtype: list
    #     """
    #     if domain is None:
    #         domain = []
    #     ext_filter = ast.literal_eval(
    #         str(self.backend_record.external_carrier_domain_filter)
    #     )
    #     domain += ext_filter or []
    #     return super(DeliveryRegionAdapter, self).search(
    #         domain=domain, model=model, offset=offset, limit=limit, order=order
    #     )


class DeliveryRegionListener(Component):
    _name = "delivery.region.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["delivery.region"]
    _usage = "event.listener"
