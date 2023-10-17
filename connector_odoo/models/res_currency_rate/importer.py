# Copyright 2022 Greenice, S.L.
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class ResCurrencyRateBatchImporter(Component):
    _name = "odoo.res.currency.rate.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.res.currency.rate"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo currency rates %s returned %s items",
            domain,
            len(external_ids),
        )
        base_priority = 10
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class ResCurrencyRateMapper(Component):
    _name = "odoo.res.currency.rate.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.res.currency.rate"

    direct = [
        ("name", "name"),
        ("rate", "rate"),
    ]

    @mapping
    def check_currency_rate_exists(self, record):
        res = {}
        currency_id = self.binder_for("odoo.res.currency").to_internal(
            record["currency_id"][0], unwrap=True
        )
        rate_id = self.env["res.currency.rate"].search(
            [
                ("name", "=", record["name"]),
                ("currency_id", "=", currency_id.id),
            ]
        )
        if len(rate_id) == 1:
            _logger.info(
                "Res currency rate found for %s : %s" % (record["name"], rate_id.name)
            )
            res.update({"odoo_id": rate_id.id})
        return res

    @only_create
    @mapping
    def currency_id(self, record):
        binder = self.binder_for("odoo.res.currency")
        currency_id = binder.to_internal(record["currency_id"][0], unwrap=True)
        return {"currency_id": currency_id.id}


class CurrencyRateImporter(Component):
    """Import Odoo Currency"""

    _name = "odoo.res.currency.rate.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.res.currency.rate"

    def _import_dependencies(self, force=False):
        self._import_dependency(
            self.odoo_record["currency_id"][0],
            "odoo.res.currency",
            force=force,
        )
        return super()._import_dependencies(force=force)
