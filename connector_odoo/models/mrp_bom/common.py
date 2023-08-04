# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo import fields, models

from odoo.addons.component.core import Component

_logger = logging.getLogger(__name__)


class OdooMrpBom(models.Model):
    _name = "odoo.mrp.bom"
    _inherit = "odoo.binding"
    _inherits = {"mrp.bom": "odoo_id"}
    _description = "External Odoo MRP BOM"
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
        return self.with_delay().import_record(
            self.backend_id, self.external_id, force=True
        )


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    bind_ids = fields.One2many(
        comodel_name="odoo.mrp.bom",
        inverse_name="odoo_id",
        string="Odoo Bindings",
    )


class MrpBomAdapter(Component):
    _name = "odoo.mrp.bom.adapter"
    _inherit = "odoo.adapter"
    _apply_on = "odoo.mrp.bom"

    _odoo_model = "mrp.bom"

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
            str(self.backend_record.external_bom_domain_filter)
        )
        domain += ext_filter or []
        return super(MrpBomAdapter, self).search(
            domain=domain, model=model, offset=offset, limit=limit, order=order
        )


class MrpBomListener(Component):
    _name = "mrp.bom.listener"
    _inherit = "base.connector.listener"
    _apply_on = ["mrp.bom"]
    _usage = "event.listener"
