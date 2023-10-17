# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class DeliveryPriceRuleBatchImporter(Component):
    """Import the Carrier Price Rules."""

    _name = "odoo.delivery.price.rule.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.delivery.price.rule"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for delivery carriers %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class DeliveryCarrierMapper(Component):
    _name = "odoo.delivery.price.rule.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.delivery.price.rule"]

    direct = [
        ("sequence", "sequence"),
        ("variable", "variable"),
        ("operator", "operator"),
        ("max_value", "max_value"),
        ("list_base_price", "list_base_price"),
        ("list_price", "list_price"),
        ("variable_factor", "variable_factor"),
    ]

    @mapping
    def region_id(self, record):
        vals = {}
        binder = self.binder_for("odoo.delivery.region")
        region = record["region_id"]
        if region:
            local_region = binder.to_internal(region[0], unwrap=True)
            vals["region_id"] = local_region.id
        return vals

    @mapping
    def carrier_id(self, record):
        vals = {}
        binder = self.binder_for("odoo.delivery.carrier")
        carrier = record["carrier_id"]
        if carrier:
            local_carrier = binder.to_internal(carrier[0], unwrap=True)
            vals["carrier_id"] = local_carrier.id
        return vals


class DeliveryPriceRuleImporter(Component):
    _name = "odoo.delivery.price.rule.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.delivery.price.rule"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        super()._import_dependencies(force=force)
        record = self.odoo_record
        if region := record.get("region_id"):
            self._import_dependency(region[0], "odoo.delivery.region", force=force)
        if carrier_id := record.get("carrier_id"):
            self._import_dependency(carrier_id[0], "odoo.delivery.carrier", force=force)
