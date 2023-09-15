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

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo Address District %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class AddressDistrictImportMapper(Component):
    _name = "odoo.address.district.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.address.district"]

    direct = [
        ("name", "name"),
    ]

    # We are already doing ID -> ID mapping in the backend adapter.
    # No need to match with the name.
    # @only_create
    # @mapping
    # def check_address_group_exists(self, record):
    #     res = {}
    #     ctx = {"lang": self.backend_record.get_default_language_code()}
    #     district_record = (
    #         self.env["address.district"]
    #         .with_context(ctx)
    #         .search(
    #             [
    #                 ("name", "=", record["name"]),
    #                 ("state_id.display_name", "=", record["state_id"][1]),
    #             ],
    #             limit=1,
    #         )
    #     )
    #     if district_record:
    #         _logger.info(
    #             "Address District found for %s : %s" % (record, district_record)
    #         )
    #         res.update({"odoo_id": district_record.id})
    #     return res

    @mapping
    def state_id(self, record):
        ctx = {"lang": self.backend_record.get_default_language_code()}
        remote_state = self.work.odoo_api.browse(
            model="res.country.state", res_id=record["state_id"][0]
        )
        state_record = (
            self.env["res.country.state"]
            .with_context(ctx)
            .search(
                [
                    "&",
                    ("name", "=", remote_state["name"]),
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
        if state_record.name != remote_state["name"]:
            raise ValidationError(
                _(
                    "State found for country %s but names are different:"
                    " Local: %s, Remote: %s"
                    % (
                        self.env.ref("base.tr").name,
                        state_record.name,
                        remote_state["name"],
                    )
                )
            )
        return {"state_id": state_record.id}


class AddressDistrictImporter(Component):
    _name = "odoo.address.district.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.address.district"]
