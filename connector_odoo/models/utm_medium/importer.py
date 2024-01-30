# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class UTMMediumBatchImporter(Component):
    _name = "odoo.utm.medium.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.utm.medium"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo utm medium %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class UTMMediumMapper(Component):
    _name = "odoo.utm.medium.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.utm.medium"

    direct = [
        ("name", "name"),
    ]

    @only_create
    @mapping
    def odoo_id(self, record):
        vals = {}
        exist_medium = self.env["utm.medium"].search(
            [("name", "=", record["name"])], limit=1
        )
        if exist_medium:
            vals["odoo_id"] = exist_medium.id
        return vals


class UTMMediumImporter(Component):

    _name = "odoo.utm.medium.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.utm.medium"

    def _create(self, data):
        """
        When creating new binding, if there is any odoo_id, we should remove all the
        keys and just keep the odoo_id key. So it means we would create a new binding
        for the odoo_id.
        """
        if data.get("odoo_id"):
            data = {
                "odoo_id": data["odoo_id"],
                "backend_id": self.backend_record.id,
            }
        return super(UTMMediumImporter, self)._create(data)
