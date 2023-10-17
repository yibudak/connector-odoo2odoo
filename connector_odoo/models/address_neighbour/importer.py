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
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class AddressNeighbourImportMapper(Component):
    _name = "odoo.address.neighbour.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.address.neighbour"]

    direct = [
        ("name", "name"),
        ("code", "code"),
    ]

    # We are already doing ID -> ID mapping in the backend adapter.
    # No need to match with the name.
    # @only_create
    # @mapping
    # def check_address_neighbour_exists(self, record):
    #     res = {}
    #     ctx = {"lang": self.backend_record.get_default_language_code()}
    #     neighbour_record = (
    #         self.env["address.neighbour"]
    #         .with_context(ctx)
    #         .search(
    #             [
    #                 ("name", "=", record.name),
    #                 ("region_id.name", "=", record.region_id.name),
    #                 ("district_id.name", "=", record.district_id.name),
    #                 ("state_id.name", "=", record.state_id.name)
    #             ],
    #             limit=1,
    #         )
    #     )
    #     if neighbour_record:
    #         _logger.info(
    #             "Address Neighbour found for %s : %s" % (record, neighbour_record)
    #         )
    #         res.update({"odoo_id": neighbour_record.id})
    #     return res

    @mapping
    def region_id(self, record):
        vals = {}
        if region_id := record["region_id"]:
            binder = self.binder_for("odoo.address.region")
            local_region_id = binder.to_internal(region_id[0], unwrap=True)
            if not local_region_id:
                raise ValidationError(
                    _(
                        "Region %s not found for neighbour %s"
                        % (record["region_id"][1], record["name"])
                    )
                )
            vals.update({"region_id": local_region_id.id})
        return vals


class AddressNeighbourImporter(Component):
    _name = "odoo.address.neighbour.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.address.neighbour"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if region := record.get("region_id"):
            self._import_dependency(region[0], "odoo.address.region", force=force)
        return super()._import_dependencies()
