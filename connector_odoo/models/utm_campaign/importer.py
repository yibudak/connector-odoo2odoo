# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class UTMCampaignBatchImporter(Component):
    _name = "odoo.utm.campaign.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.utm.campaign"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo utm campaign %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class UTMCampaignMapper(Component):
    _name = "odoo.utm.campaign.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.utm.campaign"

    direct = [
        ("name", "name"),
    ]

    @only_create
    @mapping
    def odoo_id(self, record):
        vals = {}
        exist_campaign = self.env["utm.campaign"].search(
            [("name", "=", record["name"])], limit=1
        )
        if exist_campaign:
            vals["odoo_id"] = exist_campaign.id
        return vals


class UTMCampaignImporter(Component):

    _name = "odoo.utm.campaign.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.utm.campaign"

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
        return super(UTMCampaignImporter, self)._create(data)
