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

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo Address Region %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class AddressRegionImportMapper(Component):
    _name = "odoo.address.region.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.address.region"]

    direct = [
        ("name", "name"),
    ]

    # We are already doing ID -> ID mapping in the backend adapter.
    # No need to match with the name.
    # @only_create
    # @mapping
    # def check_address_region_exists(self, record):
    #     res = {}
    #     ctx = {"lang": self.backend_record.get_default_language_code()}
    #     region_record = (
    #         self.env["address.region"]
    #         .with_context(ctx)
    #         .search(
    #             [
    #                 ("name", "=", record.name),
    #                 ("district_id.name", "=", record.district_id.name),
    #                 ("state_id.name", "=", record.state_id.name)
    #             ],
    #             limit=1,
    #         )
    #     )
    #     if region_record:
    #         _logger.info(
    #             "Address Region found for %s : %s" % (record, region_record)
    #         )
    #         res.update({"odoo_id": region_record.id})
    #     return res

    @mapping
    def district_id(self, record):
        vals = {}
        if district_id := record["district_id"]:
            binder = self.binder_for("odoo.address.district")
            local_district_id = binder.to_internal(district_id[0], unwrap=True)
            if not local_district_id:
                raise ValidationError(
                    _(
                        "District %s not found for state %s"
                        % (record.district_id.name, record.state_id.name)
                    )
                )
            vals.update({"district_id": local_district_id.id})
        return vals


class AddressRegionImporter(Component):
    _name = "odoo.address.region.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.address.region"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if district := record.get("district_id"):
            self._import_dependency(district[0], "odoo.address.district", force=force)
