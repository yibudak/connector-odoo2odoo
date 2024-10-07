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

    duplicate = fields.Boolean(
        string="Duplicate",
        help="If this job is a duplicate of another job, this field is True.",
        readonly=True,
        compute="_compute_duplicate",
    )

    def _compute_duplicate(self):
        for record in self:
            duplicate_job = self.search(
                [
                    ("func_string", "=", record.func_string),
                    ("state", "in", ("pending", "enqueued", "started")),
                    ("model_name", "=", record.model_name),
                    ("channel", "=", record.channel),
                    ("id", "!=", record.id),
                ],
                limit=1,
            )
            record.duplicate = bool(duplicate_job)
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override the create method to set the state of the duplicate jobs to "done".
        """
        res = super(JobQueue, self).create(vals_list)
        for record in res:
            if record.duplicate:
                record.state = "done"
