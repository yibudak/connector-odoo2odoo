# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class UomBatchImporter(Component):
    _name = "odoo.uom.uom.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.uom.uom"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""
        external_ids = self.backend_adapter.search(
            domain,
        )
        _logger.info(
            "search for odoo uom %s returned %s items", domain, len(external_ids)
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class UomMapper(Component):
    _name = "odoo.uom.uom.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.uom.uom"

    direct = [
        ("name", "name"),
        ("factor_inv", "factor_inv"),
        ("factor", "factor"),
        ("uom_type", "uom_type"),
        ("rounding", "rounding"),
        ("active", "active"),
    ]

    @mapping
    def category_id(self, record):
        """UOM category is manually created by user"""
        manual_categ_mapping = {
            1: 1,
            2: 2,
            3: 3,
            4: 4,
            5: 6,
            7: 7,
            8: 8,
        }

        category_id = record["category_id"][0]
        return {"category_id": manual_categ_mapping[category_id]}

    @only_create
    @mapping
    def check_uom_exists(self, record):
        res = {}
        category_name = record["category_id"][1]
        lang = self.backend_record.get_default_language_code()
        _logger.info("CHECK ONLY CREATE UOM %s with lang %s" % (record["name"], lang))

        local_uom_id = (
            self.env["uom.uom"]
            .with_context(lang=lang)
            .search(
                [
                    ("name", "=", record["name"]),
                    ("category_id.name", "=", category_name),
                ],
                limit=1,
            )
        )
        _logger.info("UOM found for %s : %s" % (record, local_uom_id))
        if local_uom_id:
            res.update({"odoo_id": local_uom_id.id})
        return res


class UoMImporter(Component):
    """Import Odoo UOM"""

    _name = "odoo.uom.uom.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.uom.uom"
