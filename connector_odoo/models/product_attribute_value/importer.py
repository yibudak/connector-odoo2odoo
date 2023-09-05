# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class ProductAttributeValueImporter(Component):
    """Import Odoo Attribute Value"""

    _name = "odoo.product.attribute.value.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.product.attribute.value"

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if attribute_id := record["attribute_id"]:
            self._import_dependency(
                attribute_id[0], "odoo.product.attribute", force=force
            )


class ProductAttributeValueMapper(Component):
    _name = "odoo.product.attribute.value.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.product.attribute.value"

    direct = [
        ("name", "name"),
        ("numeric_value", "numeric_value"),
    ]

    def get_attribute_id(self, record):
        binder = self.binder_for("odoo.product.attribute")
        local_attribute_id = binder.to_internal(record["attribute_id"][0], unwrap=True)
        return local_attribute_id.id

    @mapping
    def attribute_id(self, record):
        return {"attribute_id": self.get_attribute_id(record)}

    @only_create
    @mapping
    def check_att_value_exists(self, record):
        if not record.get("name"):
            return {}
        lang = self.backend_record.get_default_language_code()
        att_id = self.get_attribute_id(record)
        value_id = (
            self.env["product.attribute.value"]
            .with_context(lang=lang)
            .search(
                [
                    ("attribute_id", "=", att_id),
                    ("name", "=", record.get("name")),
                ],
                limit=1,
            )
        )
        vals = {}
        if value_id:
            vals["odoo_id"] = value_id.id
        return vals
