# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class ProductTemlateAttributeValueImporter(Component):
    """Import Odoo Attribute Value"""

    _name = "odoo.product.template.attribute.value.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.product.template.attribute.value"

    # def _import_dependencies(self, force=False):
    #     """Import the dependencies for the record"""
    #     record = self.odoo_record
    #     self._import_dependency(
    #         record.attribute_id.id, "odoo.product.attribute", force=force
    #     )


class ProductTemplateAttributeValueMapper(Component):
    _name = "odoo.product.template.attribute.value.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.product.template.attribute.value"

    direct = [
        ("name", "name"),
    ]

    @mapping
    def attribute_id(self, record):
        binder = self.binder_for("odoo.product.attribute")
        local_attribute_id = binder.to_internal(record.attribute_id.id, unwrap=True)
        return {"attribute_id": local_attribute_id.id}

    @mapping
    def attribute_value_id(self, record):
        binder = self.binder_for("odoo.product.attribute.value")
        local_attribute_value_id = binder.to_internal(record.product_attribute_value_id.id, unwrap=True)
        return {"product_attribute_value_id": local_attribute_value_id.id}

    @only_create
    @mapping
    def product_tmpl_id(self, record):
        binder = self.binder_for("odoo.product.template")
        local_product_tmpl_id = binder.to_internal(record.product_tmpl_id.id, unwrap=True)
        return {"product_tmpl_id": local_product_tmpl_id.id}

    # @only_create
    # @mapping
    # def check_att_value_exists(self, record):
    #     # TODO: Improve and check family, factor etc...
    #     lang = (
    #         self.backend_record.default_lang_id.code
    #         or self.env.user.lang
    #         or self.env.context["lang"]
    #         or "en_US"
    #     )
    #     att_id = self.get_attribute_id(record)
    #
    #     value_id = self.env["product.attribute.value"].with_context(lang=lang).search(
    #         [
    #             ("name", "=", record.name),
    #             ("attribute_id", "=", att_id),
    #         ], limit=1
    #     )
    #     res = {}
    #     if len(value_id) > 0:
    #         res.update({"odoo_id": value_id.id})
    #     return res or False
