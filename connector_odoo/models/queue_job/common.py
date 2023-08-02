# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import models, fields, api, _


class JobQueue(models.Model):
    _inherit = "queue.job"

    odoo_binding_model_name = fields.Char(
        string="Odoo Binding Model Name",
        help="The name of the Odoo binding model that this job is related to.",
        readonly=True,
    )
    odoo_binding_id = fields.Integer(
        string="Odoo Binding ID",
        help="The ID of the Odoo binding that this job is related to.",
        readonly=True,
    )
