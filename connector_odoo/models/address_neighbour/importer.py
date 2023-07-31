import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AddressNeighbourBatchImporter(Component):
    """Import the Odoo Address District."""

    _name = "odoo.address.neighbour.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.address.neighbour"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo Address Neighbour %s returned %s items",
            domain,
            len(external_ids),
        )
        base_priority = 10
        for external_id in external_ids:
            job_options = {"priority": base_priority}
            self._import_record(external_id, job_options=job_options, force=force)


class AddressNeighbourImportMapper(Component):
    _name = "odoo.address.neighbour.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.address.neighbour"]

    direct = [
        ("name", "name"),
        ("code", "code"),
    ]

    @only_create
    @mapping
    def check_address_neighbour_exists(self, record):
        res = {}
        ctx = {"lang": self.backend_record.get_default_language_code()}
        neighbour_record = (
            self.env["address.neighbour"]
            .with_context(ctx)
            .search(
                [
                    ("name", "=", record.name),
                    ("region_id.name", "=", record.region_id.name),
                    ("district_id.name", "=", record.district_id.name),
                    ("state_id.name", "=", record.state_id.name)
                ],
                limit=1,
            )
        )
        if neighbour_record:
            _logger.info(
                "Address Neighbour found for %s : %s" % (record, neighbour_record)
            )
            res.update({"odoo_id": neighbour_record.id})
        return res

    @mapping
    def region_id(self, record):
        ctx = {"lang": self.backend_record.get_default_language_code()}
        region_record = (
            self.env["address.region"]
            .with_context(ctx)
            .search(
                [
                    ("name", "=", record.region_id.name),
                    ("district_id.name", "=", record.district_id.name),
                    ("state_id.name", "=", record.state_id.name)
                ],
                limit=1,
            )
        )
        if not region_record:
            raise ValidationError(
                _(
                    "Region %s not found for state %s"
                    % (record.region_id.name, record.state_id.name)
                )
            )
        return {"region_id": region_record.id}


class AddressNeighbourImporter(Component):
    _name = "odoo.address.neighbour.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.address.neighbour"]

