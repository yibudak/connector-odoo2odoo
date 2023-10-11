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
        prefix = record["code_prefix"].split(".")
        domain = [("code_prefix_start", "=", prefix[0])]
        if len(prefix) > 1:
            domain.append(("code_prefix_end", "=", prefix[1]))
        account_id = self.env["account.group"].search(domain)
        if len(account_id) == 1:
            _logger.info(
                "Account Group found for %s : %s" % (record["name"], account_id.name)
            )
            res.update({"odoo_id": account_id.id})
        return res

    @mapping
    def parent_id(self, record):
        # todo: samet
        res = {}
        parent_id = record.get("parent_id")
        if parent_id:
            binder = self.binder_for("odoo.account.group")
            local_parent = binder.to_internal(parent_id[0], unwrap=True)
            if local_parent:
                res.update({"parent_id": local_parent.id})
        return res

    @mapping
    def prefix(self, record):
        # todo: samet
        code_prefix = record["code_prefix"].split(".")
        vals = {"code_prefix_start": code_prefix[0], "code_prefix_end": ""}
        if len(code_prefix) > 1:
            vals.update({"code_prefix_end": code_prefix[1]})
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
