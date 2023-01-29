import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AddressRegionBatchImporter(Component):
    """Import the Odoo Address District."""

    _name = "odoo.address.region.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.address.region"]

    def run(self, filters=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(filters)
        _logger.debug(
            "search for odoo Address Region %s returned %s items",
            filters,
            len(external_ids),
        )
        base_priority = 10
        for external_id in external_ids:
            job_options = {"priority": base_priority}
            self._import_record(external_id, job_options=job_options, force=force)


class AddressRegionImportMapper(Component):
    _name = "odoo.address.region.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.address.region"]

    direct = [
        ("name", "name"),
    ]

    @only_create
    @mapping
    def check_address_region_exists(self, record):
        res = {}
        ctx = {"lang": self.backend_record.get_default_language_code()}
        region_record = (
            self.env["address.region"]
            .with_context(ctx)
            .search(
                [
                    ("name", "=", record.name),
                    ("district_id.name", "=", record.district_id.name),
                    ("state_id.name", "=", record.state_id.name)
                ],
                limit=1,
            )
        )
        if region_record:
            _logger.debug(
                "Address Region found for %s : %s" % (record, region_record)
            )
            res.update({"odoo_id": region_record.id})
        return res

    @mapping
    def district_id(self, record):
        ctx = {"lang": self.backend_record.get_default_language_code()}
        district_record = (
            self.env["address.district"]
            .with_context(ctx)
            .search(
                [
                    ("name", "=", record.district_id.name),
                    ("state_id.name", "=", record.district_id.state_id.name),
                ],
                limit=1,
            )
        )
        if not district_record:
            raise ValidationError(
                _(
                    "District %s not found for state %s"
                    % (record.district_id.name, record.state_id.name)
                )
            )
        return {"district_id": district_record.id}


class AddressRegionImporter(Component):
    _name = "odoo.address.region.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.address.region"]

