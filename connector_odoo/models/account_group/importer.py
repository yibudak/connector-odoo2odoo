import logging

from odoo import _
from odoo.exceptions import ValidationError

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class AccountGroupBatchImporter(Component):
    """Import the Odoo Account Group.

    For every Account Group in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.account.group.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.account.group"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo Account Group %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class AccountGroupImportMapper(Component):
    _name = "odoo.account.group.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.account.group"]

    direct = [
        ("name", "name"),
    ]

    @only_create
    @mapping
    def check_account_group_exists(self, record):
        res = {}
        if code_prefix := record.get("code_prefix"):
            splitted_code_prefix = code_prefix.split(".")
            domain = [("code_prefix_start", "=", splitted_code_prefix[0])]
            if len(splitted_code_prefix) > 1:
                domain.append(("code_prefix_end", "=", splitted_code_prefix[1]))
            if account_id := self.env["account.group"].search(domain):
                _logger.info(
                    "Account Group found for %s : %s"
                    % (record["name"], account_id.name)
                )
                res.update({"odoo_id": account_id.id})
        return res

    @mapping
    def parent_id(self, record):
        vals = {"parent_id": False}
        if parent_id := record.get("parent_id"):
            binder = self.binder_for("odoo.account.group")
            local_parent_id = binder.to_internal(parent_id[0], unwrap=True)
            if local_parent_id:
                vals.update({"parent_id": local_parent_id.id})
        return vals

    @mapping
    def prefix(self, record):
        vals = {"code_prefix_start": False, "code_prefix_end": False}
        if code_prefix := record.get("code_prefix"):
            splitted_code_prefix = code_prefix.split(".")
            vals.update({"code_prefix_start": splitted_code_prefix[0]})
            if len(splitted_code_prefix) > 1:
                vals.update({"code_prefix_end": splitted_code_prefix[1]})
        return vals


class AccountGroupImporter(Component):
    _name = "odoo.account.group.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.account.group"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if record.get("parent_id"):
            self._import_dependency(
                record["parent_id"][0], "odoo.account.group", force=force
            )
