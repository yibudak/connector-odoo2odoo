# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class DeliveryRegionBatchImporter(Component):
    """Import the Carriers."""

    _name = "odoo.delivery.region.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.delivery.region"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for delivery regions %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options)

    # def _import_dependencies(self, force=False):
    #     """Import the dependencies for the record"""
    #     record = self.odoo_record
    #     self._import_dependency(
    #         record.product_id.id, "odoo.product.product", force=force
    #     )


class DeliveryRegionMapper(Component):
    _name = "odoo.delivery.region.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.delivery.region"]

    direct = [
        ("name", "name"),
    ]

    @mapping
    def country_ids(self, record):
        res = {}
        countries = record.get("country_ids")
        if countries:
            external_countries = self.work.odoo_api.search(
                model="res.country", domain=[("id", "in", countries)]
            )
            local_countries = self.env["res.country"].search(
                [("code", "in", [x["code"] for x in external_countries])]
            )
            res["country_ids"] = [(6, 0, local_countries.ids)]
        return res

    @mapping
    def state_ids(self, record):
        res = {}
        state_list = []
        states = record.get("state_ids")
        if states:
            for state in states:
                external_state = self.work.odoo_api.browse(
                    model="res.country.state", res_id=state
                )
                local_state = self.env["res.country.state"].search(
                    [
                        ("code", "=", external_state["code"]),
                        ("country_id.name", "=", external_state["country_id"][1]),
                    ]
                )
                if local_state:
                    state_list.append(local_state)
            res["state_ids"] = [(6, 0, state_list)]
        return res


class DeliveryRegionImporter(Component):
    _name = "odoo.delivery.region.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.delivery.region"]
