# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class ProductCategoryBatchImporter(Component):
    """Import the Odoo Product Categories.

    For every product category in the list, a delayed job is created.
    A priority is set on the jobs according to their level to rise the
    chance to have the top level categories imported first.
    """

    _name = "odoo.product.category.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.product.category"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        updated_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo product categories %s returned %s items",
            domain,
            len(updated_ids),
        )
        for cat in updated_ids:
            self._import_record(cat, force=force)


class ProductCategoryImporter(Component):
    _name = "odoo.product.category.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.category"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        # import parent category
        # the root category has a 0 parent_id
        if parent := record["parent_id"]:
            self._import_dependency(parent[0], self.model, force=force)

    def _after_import(self, binding, force=False):
        """Hook called at the end of the import"""
        self._create_public_category(binding)
        binding._parent_store_compute()
        return super()._after_import(binding, force)

    def _create_public_category(self, binding):
        """Create a public category for the binding"""
        categ_id = binding.odoo_id

        public_categ_id = self.env["product.public.category"].search(
            [("origin_categ_id", "=", categ_id.id)]
        )
        parent_id = self.env["product.public.category"].search(
            [("origin_categ_id", "=", categ_id.parent_id.id)]
        )

        vals = {
            "name": categ_id.name,
            "sequence": categ_id.sequence,
            "origin_categ_id": categ_id.id,
            "website_id": self.env.user.company_id.website_id.id,
            "parent_id": parent_id.id or False,
        }

        if not public_categ_id:
            public_categ_id = self.env["product.public.category"].create(vals)
            _logger.info(
                "created public category %s for odoo product category %s",
                public_categ_id,
                binding,
            )
        else:
            public_categ_id.write(vals)
            _logger.info(
                "writed public category %s for odoo product category %s",
                public_categ_id,
                binding,
            )
        public_categ_id._compute_product_tmpls()
        public_categ_id._parent_store_compute()
        return True


class ProductCategoryImportMapper(Component):
    _name = "odoo.product.category.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.product.category"

    direct = [
        ("name", "name"),
        ("sequence", "sequence"),
        ("is_published", "is_published"),
        ("pricelist_discount_scales", "pricelist_discount_scales"),
        ("show_in_pricelist", "show_in_pricelist"),
        ("ecommerce_image", "ecommerce_image"),
    ]

    @mapping
    def parent_id(self, record):
        vals = {"parent_id": False, "odoo_parent_id": False}
        if not (parent := record.get("parent_id")):
            return vals
        binder = self.binder_for()
        parent_binding = binder.to_internal(parent[0])

        if not parent_binding:
            raise MappingError(
                "The product category with "
                "Odoo id %s is not imported." % record.parent_id.id
            )

        parent = parent_binding.odoo_id
        vals.update({"parent_id": parent.id, "odoo_parent_id": parent_binding.id})
        return vals
