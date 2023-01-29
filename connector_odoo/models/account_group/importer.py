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

    def run(self, filters=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(filters)
        _logger.debug(
            "search for odoo Account Group %s returned %s items",
            filters,
            len(external_ids),
        )
        base_priority = 10
        for external_id in external_ids:
            group_id = self.backend_adapter.read(external_id)
            parents = group_id.parent_path.split("/")
            job_options = {"priority": base_priority + len(parents) or 0}
            self._import_record(external_id, job_options=job_options, force=force)


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
        prefix = record.code_prefix.split(".")
        domain = [("code_prefix_start", "=", prefix[0])]
        if len(prefix) > 1:
            domain.append(("code_prefix_end", "=", prefix[1]))
        account_id = self.env["account.group"].search(domain)
        _logger.debug("Account Group found for %s : %s" % (record, account_id))
        if len(account_id) == 1:
            res.update({"odoo_id": account_id.id})
        return res

    @mapping
    def parent_id(self, record):
        res = {}
        parent_id = record.parent_id
        binder = self.binder_for("odoo.account.group")
        if parent_id:
            local_parent = binder.to_internal(parent_id.id, unwrap=True)
            if local_parent:
                res.update({"parent_id": local_parent.id})
        return res

    @mapping
    def prefix(self, record):
        code_prefix = record.code_prefix.split(".")
        vals = {"code_prefix_start": code_prefix[0], "code_prefix_end": ""}
        if len(code_prefix) > 1:
            vals.update({"code_prefix_end": code_prefix[1]})
        return vals


class AccountGroupImporter(Component):
    _name = "odoo.account.group.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.account.group"]
