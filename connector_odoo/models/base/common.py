# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import models, fields


class Base(models.AbstractModel):
    _inherit = "base"

    active_job_ids = fields.One2many(
        "queue.job",
        compute="_compute_active_job_ids",
        store=False,
    )

    def _compute_active_job_ids(self):
        """
        Add active job ids to the recordset.
        """
        for record in self:
            if record.id and hasattr(record, "bind_ids"):
                record.active_job_ids = self.env["queue.job"].search(
                    [
                        ("odoo_binding_model_name", "=", record._name),
                        ("odoo_binding_id", "=", record.id),
                        ("state", "!=", "done"),
                    ]
                )
            else:
                record.active_job_ids = False
