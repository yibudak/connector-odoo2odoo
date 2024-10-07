# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.exceptions import ValidationError
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class ProductTemlateAttributeLineImporter(Component):
    """Import Odoo Product Attribute Line"""

    _name = "odoo.product.template.attribute.line.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.product.template.attribute.line"

    def _get_binding_with_data(self, binding):
        if not binding:
            attr_id_binding = self.env["odoo.product.template.attribute.line"].search(
                [
                    (
                        "product_tmpl_id.bind_ids.external_id",
                        "=",
                        self.odoo_record["product_tmpl_id"][0],
                    ),
                    (
                        "attribute_id.bind_ids.external_id",
                        "=",
                        self.odoo_record["attribute_id"][0],
                    ),
                    "|",
                    ("active", "=", False),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if attr_id_binding:
                binding = attr_id_binding
        return binding

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if value_ids := record["value_ids"]:
            for value in value_ids:
                self._import_dependency(
                    value, "odoo.product.attribute.value", force=force
                )


class ProductTemplateAttributeLineMapper(Component):
    _name = "odoo.product.template.attribute.line.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.product.template.attribute.line"

    def _get_product_tmpl_id(self, record):
        binder = self.binder_for("odoo.product.template")
        return binder.to_internal(record["product_tmpl_id"][0], unwrap=True).id

    def _get_attribute_id(self, record):
        binder = self.binder_for("odoo.product.attribute")
        return binder.to_internal(record["attribute_id"][0], unwrap=True).id

    def _get_attribute_value_id(self, record):
        binder = self.binder_for("odoo.product.attribute.value")
        vals = []
        for value_id in record["value_ids"]:
            local_attribute_value_id = binder.to_internal(value_id, unwrap=True)
            if local_attribute_value_id:
                vals.append(local_attribute_value_id.id)
            else:
                ValidationError("Attribute value %s is not imported yet" % value_id)
        return vals

    @mapping
    def attribute_value_id(self, record):
        return {"value_ids": [(6, 0, self._get_attribute_value_id(record))]}

    @mapping
    def attribute_id(self, record):
        return {"attribute_id": self._get_attribute_id(record)}

    @only_create
    @mapping
    def product_tmpl_id(self, record):
        return {"product_tmpl_id": self._get_product_tmpl_id(record)}

    @mapping
    def active(self, record):
        # We don't have any active field in Odoo 12, just set it True
        return {"active": True}

    @mapping
    def default_value_id(self, record):
        vals = {"default_value_id": False}
        if record.get("default_value_id"):
            binder = self.binder_for("odoo.product.attribute.value")
            local_attribute_value_id = binder.to_internal(
                record["default_value_id"][0], unwrap=True
            )
            if local_attribute_value_id:
                vals["default_value_id"] = local_attribute_value_id.id
            else:
                ValidationError(
                    "Attribute value %s is not imported yet"
                    % record["default_value_id"]
                )
        return vals
