# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import api, models


class ProductTemplateAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"

    @api.constrains("active", "value_ids", "attribute_id")
    def _check_valid_values(self):
        """
        Since we are importing Ptav's from Odoo 12, we don't need to
        check if the values are valid or not.
        """
        return True
