# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import ast
import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooPartner(models.Model):
    _special_channel = "root.2"
    _queue_priority = 3
    _name = "odoo.res.partner"
    _inherit = "odoo.binding"
    _inherits = {"res.partner": "odoo_id"}
    _description = "External Odoo Partner"

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
        return self.delayed_import_record(self.backend_id, self.external_id, force=True)


class Partner(models.Model):
    _inherit = "res.partner"

    bind_ids = fields.One2many(
        comodel_name="odoo.res.partner",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )

    def unlink(self):
        for partner in self:
            if partner.bind_ids:
                partner.bind_ids.unlink()
        return super(Partner, self).unlink()

    def get_remote_risk_credit_limit(self):
        res = {}
        for partner in self:
            context = {}
            bindings = partner.bind_ids
            if not bindings:
                continue
            binding = bindings[0]
            with binding.backend_id.work_on("odoo.res.partner") as work:
                adapter = work.component(usage="record.importer").backend_adapter
                data = adapter.read(binding.external_id, context=context)
                res[partner.id] = {
                    "risk_currency_id": data.get("risk_currency_id", 0),
                    "risk_total": data.get("risk_total", 0),
                    "credit_limit": data.get("credit_limit", 0),
                }
        return res


class PartnerAdapter(Component):
    _name = "odoo.res.partner.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.res.partner"

    _odoo_model = "res.partner"

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
            str(self.backend_record.external_res_partner_domain_filter)
        )
        domain += ext_filter or []
        return super(PartnerAdapter, self).search(
            domain=domain, model=model, offset=offset, limit=limit, order=order
        )


class PartnerListener(Component):
    _name = "res.partner.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["res.partner"]
    _usage = "event.listener"
