# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging
import string
import secrets
from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo import SUPERUSER_ID

_logger = logging.getLogger(__name__)


class ResUsersBatchImporter(Component):
    _name = "odoo.res.users.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.res.users"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo res users %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class ResUsersMapper(Component):
    _name = "odoo.res.users.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.res.users"

    direct = [
        ("login", "login"),
    ]

    @mapping
    def active(self, record):
        """
        odoo/addons/base/models/res_users.py:596
        Do not add active field for superuser
        """
        if record["id"] != SUPERUSER_ID:
            return record["active"]
        else:
            return {}

    @mapping
    def partner_id(self, record):
        binder = self.binder_for("odoo.res.partner")
        partner_id = binder.to_internal(record["partner_id"][0], unwrap=True)
        return {"partner_id": partner_id.id}

    @only_create
    @mapping
    def odoo_id(self, record):
        vals = {}
        exist_user = self.env["res.users"].search(
            [
                ("login", "=", record["login"]),
                "|",
                ("active", "=", False),
                ("active", "=", True),
            ],
            limit=1,
        )
        if exist_user:
            vals["odoo_id"] = exist_user.id
        return vals

    # @only_create
    # @mapping
    # def password(self, record):
    #     def generate_password(length=15):
    #         alphabet = string.ascii_letters + string.digits
    #         password = "".join(secrets.choice(alphabet) for i in range(length))
    #         return password
    #
    #     return {"password": generate_password()}


class ResUsersImporter(Component):
    """Import Users"""

    _name = "odoo.res.users.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.res.users"

    def _create(self, data):
        """
        When creating new binding, if there is any odoo_id, we should remove all the
        keys and just keep the odoo_id key. So it means we would create a new binding
        for the odoo_id.
        """
        if data.get("odoo_id"):
            data = {"odoo_id": data["odoo_id"], "backend_id": self.backend_record.id}
        return super(ResUsersImporter, self)._create(data)

    def _import_dependencies(self, force=False):
        self._import_dependency(
            self.odoo_record["partner_id"][0],
            "odoo.res.partner",
            force=force,
        )
        return super()._import_dependencies(force=force)

    def _get_context(self):
        """Context for the create-write"""
        res = super(ResUsersImporter, self)._get_context()
        res["no_reset_password"] = True
        return res
