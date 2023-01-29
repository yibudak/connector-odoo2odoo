import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AddressDistrictBatchImporter(Component):
    """Import the Odoo Address District."""

    _name = "odoo.address.district.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.address.district"]

    def run(self, filters=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(filters)
        _logger.debug(
            "search for odoo Address District %s returned %s items",
            filters,
            len(external_ids),
        )
        base_priority = 10
        for external_id in external_ids:
            job_options = {"priority": base_priority}
            self._import_record(external_id, job_options=job_options, force=force)


class AddressDistrictImportMapper(Component):
    _name = "odoo.address.district.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.address.district"]

    direct = [
        ("name", "name"),
    ]

    @only_create
    @mapping
    def check_account_group_exists(self, record):
        res = {}
        ctx = {"lang": self.backend_record.get_default_language_code()}
        district_record = (
            self.env["address.district"]
            .with_context(ctx)
            .search(
                [
                    ("name", "=", record.name),
                    ("state_id.name", "=", record.state_id.name),
                ],
                limit=1,
            )
        )
        if district_record:
            _logger.debug(
                "Address District found for %s : %s" % (record, district_record)
            )
            res.update({"odoo_id": district_record.id})
        return res

    @mapping
    def state_id(self, record):
        ctx = {"lang": self.backend_record.get_default_language_code()}
        state_record = (
            self.env["res.country.state"]
            .with_context(ctx)
            .search(
                [
                    ("name", "=", record.state_id.name),
                    ("country_id", "=", self.env.ref("base.tr").id),
                ],
                limit=1,
            )
        )
        if not state_record:
            raise ValidationError(
                _(
                    "State %s not found for country %s"
                    % (record.state_id.name, self.env.ref("base.tr").name)
                )
            )
        return {"state_id": state_record.id}


class AddressDistrictImporter(Component):
    _name = "odoo.address.district.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.address.district"]
