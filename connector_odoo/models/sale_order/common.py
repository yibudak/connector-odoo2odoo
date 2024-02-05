# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
import ast
from odoo import fields, models, api

from odoo.addons.component.core import Component
from odoo.addons.component_event.components.event import skip_if

_logger = logging.getLogger(__name__)


class OdooSaleOrder(models.Model):
    _special_channel = "root.5"
    _queue_priority = 1
    _name = "odoo.sale.order"
    _inherit = "odoo.binding"
    _inherits = {"sale.order": "odoo_id"}
    _description = "External Odoo Sale Order"
    backend_amount_total = fields.Float()
    backend_amount_tax = fields.Float()
    backend_picking_count = fields.Integer()
    backend_date_order = fields.Datetime()
    backend_state = fields.Char()

    _sql_constraints = [
        (
            "external_id",
            "UNIQUE(external_id)",
            "External ID (external_id) must be unique!",
        ),
    ]

    def _compute_import_state(self):
        for order_id in self:
            waiting = len(
                order_id.queue_job_ids.filtered(
                    lambda j: j.state in ("pending", "enqueued", "started")
                )
            )
            error = len(order_id.queue_job_ids.filtered(lambda j: j.state == "failed"))
            if waiting:
                order_id.import_state = "waiting"
            elif error:
                order_id.import_state = "error_sync"
            elif round(order_id.backend_amount_total, 2) != round(
                order_id.amount_total, 2
            ):
                order_id.import_state = "error_amount"
            elif order_id.backend_picking_count != len(order_id.picking_ids):
                order_id.import_state = "error_sync"
            else:
                order_id.import_state = "done"

    import_state = fields.Selection(
        [
            ("waiting", "Waiting"),
            ("error_sync", "Sync Error"),
            ("error_amount", "Amounts Error"),
            ("done", "Done"),
        ],
        default="waiting",
        compute=_compute_import_state,
    )

    def name_get(self):
        result = []
        for op in self:
            name = "{} (Backend: {})".format(
                op.odoo_id.display_name, op.backend_id.display_name
            )
            result.append((op.id, name))

        return result

    def resync(self):
        return self.delayed_export_record(self.backend_id)

    @api.depends("backend_state")
    def _set_sale_state(self):
        order = self.odoo_id.with_context(connector_no_export=True)
        if self.backend_state == "draft":
            return
        # 1- If the order has the same state as the backend, do nothing
        if self.backend_state == order.state:
            return
        # 2- If the order is in a state that is not sale, do nothing
        elif self.backend_state == "done" and order.state == "sale":
            return
        # 3- If the order is sent
        elif self.backend_state == "sent":
            order.action_quotation_sent()
        # 4- If the order is a sale
        elif self.backend_state == "sale":
            order.action_confirm()
        # 5- If the order is cancelled
        elif self.backend_state == "cancel":
            order.with_context(disable_cancel_warning=True).action_cancel()

        order.date_order = self.backend_date_order
        return True


class SaleOrder(models.Model):
    _inherit = "sale.order"

    bind_ids = fields.One2many(
        comodel_name="odoo.sale.order",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )

    queue_job_ids = fields.Many2many(
        comodel_name="queue.job",
    )

    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        self._event("on_sale_order_confirm").notify(self)
        return res

    def action_cancel(self):
        res = super(SaleOrder, self).action_cancel()
        self._event("on_sale_order_cancel").notify(self)
        return res

    def action_quotation_sent(self):
        res = super(SaleOrder, self).action_quotation_sent()
        self._event("on_sale_order_quotation_sent").notify(self)
        return res


class SaleOrderAdapter(Component):
    _name = "odoo.sale.order.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.sale.order"
    _odoo_model = "sale.order"

    # Set get_passive to True to get the passive records also.
    _get_passive = True

    def search(self, domain=None, model=None, offset=0, limit=None, order=None):
        """Search records according to some criteria
        and returns a list of ids

        :rtype: list
        """
        if domain is None:
            domain = []
        ext_filter = ast.literal_eval(
            str(self.backend_record.external_sale_order_domain_filter)
        )
        domain += ext_filter or []
        return super(SaleOrderAdapter, self).search(
            domain=domain, model=model, offset=offset, limit=limit, order=order
        )


class SaleOrderListener(Component):
    _name = "odoo.sale.order.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["sale.order"]
    _usage = "event.listener"

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_sale_order_confirm(self, record):
        binding = record.bind_ids
        binding.ensure_one()
        binding.delayed_execute_method(
            binding.backend_id,
            "sale.order",
            "action_confirm",
            context={"bypass_risk": True},
        )

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_sale_order_cancel(self, record):
        binding = record.bind_ids
        binding.ensure_one()
        binding.delayed_execute_method(
            binding.backend_id,
            "sale.order",
            "action_cancel",
        )

    @skip_if(lambda self, record, **kwargs: self.no_connector_export(record))
    def on_sale_order_quotation_sent(self, record):
        binding = record.bind_ids
        binding.ensure_one()
        binding.delayed_execute_method(
            binding.backend_id,
            "sale.order",
            "action_quotation_sent",
        )
