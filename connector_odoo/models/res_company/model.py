# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = "res.company"

    default_odoo_backend_id = fields.Many2one(
        comodel_name="odoo.backend",
        string="Default Odoo Backend",
    )
