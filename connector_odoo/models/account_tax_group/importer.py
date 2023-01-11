import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AccountTaxGroupBatchImporter(Component):
    """Import the Odoo Account Group.

    For every Account Group in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.account.tax.group.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.account.tax.group"]

    def run(self, filters=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(filters)
        _logger.info(
            "search for odoo Account Tax Group %s returned %s items",
            filters,
            len(external_ids),
        )
        base_priority = 10
        for external_id in external_ids:
            job_options = {"priority": base_priority}
            self._import_record(external_id, job_options=job_options, force=force)


class AccountTaxGroupGroupImportMapper(Component):
    _name = "odoo.account.tax.group.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.account.tax.group"]

    direct = [
        ("name", "name"),
        ("sequence", "sequence"),
    ]

    @only_create
    @mapping
    def check_account_group_exists(self, record):
        res = {}
        ctx = {"lang": self.backend_record.get_default_language_code()}
        group_record = (
            self.env["account.tax.group"]
            .with_context(ctx)
            .search([("name", "=", record.name)], limit=1)
        )
        if group_record:
            _logger.debug(
                "Account Tax Group found for %s : %s" % (record, group_record)
            )
            res.update({"odoo_id": group_record.id})
        return res

    @mapping
    def country_id(self, record):
        return {"country_id": self.env.ref("base.tr").id}


class AccountTaxGroupImporter(Component):
    _name = "odoo.account.tax.group.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.account.tax.group"]
