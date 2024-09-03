# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class ProductBrandBatchImporter(Component):
    """Import the Odoo Product Brands."""

    _name = "odoo.product.brand.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.product.brand"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        updated_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo product brands %s returned %s items",
            domain,
            len(updated_ids),
        )
        for cat in updated_ids:
            self._import_record(cat, force=force)


class ProductBrandImporter(Component):
    _name = "odoo.product.brand.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.brand"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if partner := record["partner_id"]:
            self._import_dependency(partner[0], "odoo.res.partner", force=force)


class ProductBrandImportMapper(Component):
    _name = "odoo.product.brand.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.product.brand"

    direct = [
        ("name", "name"),
        ("description", "description"),
        ("logo", "logo"),
    ]

    @mapping
    def partner_id(self, record):
        vals = {"partner_id": False}
        binder = self.binder_for("odoo.res.partner")
        if partner := record["partner_id"]:
            partner_id = binder.to_internal(partner[0], unwrap=True)
            vals["partner_id"] = partner_id.id

        return vals
