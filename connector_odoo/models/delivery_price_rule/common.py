# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooDeliveryPriceRule(models.Model):
    _queue_priority = 10
    _name = "odoo.delivery.price.rule"
    _inherit = "odoo.binding"
    _inherits = {"delivery.price.rule": "odoo_id"}
    _description = "External Odoo Delivery Price Rule"
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
            return self.delayed_export_record(self.backend_id)
        else:
            return self.delayed_import_record(
                self.backend_id, self.external_id, force=True
            )


class DeliveryPriceRule(models.Model):
    _inherit = "delivery.price.rule"

    bind_ids = fields.One2many(
        comodel_name="odoo.delivery.price.rule",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class DeliveryPriceRuleAdapter(Component):
    _name = "odoo.delivery.price.rule.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.delivery.price.rule"
    _odoo_model = "delivery.price.rule"

    # Set get_passive to True to get the passive records also.
    _get_passive = False

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
    #     return super(DeliveryPriceRuleAdapter, self).search(
    #         domain=domain, model=model, offset=offset, limit=limit, order=order
    #     )


class DeliveryPriceRuleListener(Component):
    _name = "delivery.price.rule.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["delivery.price.rule"]
    _usage = "event.listener"
