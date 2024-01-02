# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.addons.component.core import Component
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class BatchAccountPaymentExporter(Component):
    _name = "odoo.account.payment.batch.exporter"
    _inherit = "odoo.delayed.batch.exporter"
    _apply_on = ["odoo.account.payment"]
    _usage = "batch.exporter"


class AccountPaymentExportMapper(Component):
    _name = "odoo.account.payment.export.mapper"
    _inherit = "odoo.export.mapper"
    _apply_on = ["odoo.account.payment"]

    direct = [
        ("name", "name"),
        ("amount", "amount"),
        ("ref", "communication"),
        ("payment_type", "payment_type"),
        ("partner_type", "partner_type"),
    ]

    @mapping
    def partner_id(self, record):
        binder = self.binder_for("odoo.res.partner")
        return {
            "partner_id": binder.to_external(record.partner_id, wrap=True),
        }

    @mapping
    def journal_id(self, record):
        return {
            "journal_id": 37,  # Sanal POS TL
        }

    @mapping
    def payment_method_id(self, record):
        return {
            "payment_method_id": 3,  # Elektronik
        }

    @mapping
    def currency_id(self, record):
        binder = self.binder_for("odoo.res.currency")
        return {
            "currency_id": binder.to_external(record.currency_id, wrap=True),
        }

    @mapping
    def payment_date(self, record):
        return {
            "payment_date": record.date.strftime(DEFAULT_SERVER_DATETIME_FORMAT),
        }

    @only_create
    @mapping
    def state(self, record):
        # v16 -> v12 always send draft except cancelled because
        # we execute post() method of the model if state is posted
        if record.state == "cancelled":
            return {"state": "cancelled"}
        else:
            return {"state": "draft"}


class OdooAccountPaymentExporter(Component):
    _name = "odoo.account.payment.exporter"
    _inherit = "odoo.exporter"
    _apply_on = ["odoo.account.payment"]

    def _export_dependencies(self):
        if self.binding.partner_id:
            self._export_dependency(self.binding.partner_id, "odoo.res.partner")

    def _create_data(self, map_record, fields=None, **kwargs):
        """Get the data to pass to :py:meth:`_create`"""
        datas = map_record.values(for_create=True, fields=fields, **kwargs)
        return datas

    def _after_export(self):
        if not self.binding.external_id:
            return

        # Check if the payment is posted or not in Odoo to prevent
        # double posting.
        exported_record = self.work.odoo_api.browse(
            model="account.payment", res_id=self.binding.external_id
        )
        if (
            exported_record
            and exported_record["state"] == "draft"
            and self.binding.state == "posted"
        ):
            self.binding.delayed_execute_method(
                self.backend_record,
                "account.payment",
                "post",
                args=[self.binding.external_id],
            )
