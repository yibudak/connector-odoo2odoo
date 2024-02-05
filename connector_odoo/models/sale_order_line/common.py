# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo import fields, models

from odoo.addons.component.core import Component
from odoo.addons.component_event.components.event import skip_if

_logger = logging.getLogger(__name__)


class OdooSaleOrderLine(models.Model):
    _queue_priority = 2
    _name = "odoo.sale.order.line"
    _inherit = "odoo.binding"
    _inherits = {"sale.order.line": "odoo_id"}
    _description = "External Odoo Sale Order Line"
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


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    bind_ids = fields.One2many(
        comodel_name="odoo.sale.order.line",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class SaleOrderLineAdapter(Component):
    _name = "odoo.sale.order.line.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.sale.order.line"

    _odoo_model = "sale.order.line"

    # Set get_passive to True to get the passive records also.
    _get_passive = False
