# from odoo import models
#
#
# class ProductTemplateAttributeLine(models.Model):
#     _inherit = "product.template.attribute.line"
#
#     def _update_product_template_attribute_values(self):
#         if self.env.context.get("no_handle_variant", False):
#             return True
#         else:
#             return super(
#                 ProductTemplateAttributeLine
#             )._update_product_template_attribute_values()
