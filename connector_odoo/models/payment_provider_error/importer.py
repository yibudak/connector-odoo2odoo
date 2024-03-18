# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class PaymentProviderErrorBatchImporter(Component):
    _name = "odoo.payment.provider.error.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.payment.provider.error"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo payment provider error %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class PaymentProviderErrorMapper(Component):
    _name = "odoo.payment.provider.error.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.payment.provider.error"

    direct = [
        ("error_code", "error_code"),
        ("error_message", "error_message"),
        ("sys_error_message", "sys_error_message"),
        ("modified_error_message", "modified_error_message"),
    ]


class PaymentProviderErrorImporter(Component):

    _name = "odoo.payment.provider.error.importer"
    _inherit = "odoo.importer"
    _apply_on = "odoo.payment.provider.error"

    def _create(self, data):
        """
        When creating new binding, if there is any odoo_id, we should remove all the
        keys and just keep the odoo_id key. So it means we would create a new binding
        for the odoo_id.
        """
        if data.get("odoo_id"):
            data = {
                "odoo_id": data["odoo_id"],
                "backend_id": self.backend_record.id,
            }
        return super(PaymentProviderErrorImporter, self)._create(data)
