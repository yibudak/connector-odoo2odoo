# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)

import logging

from odoo.addons.component.core import Component
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.addons.connector.components.mapper import mapping

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
        # yigit partnert export_dependencies'de export etmek gerekir mi?
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

    #
    # @mapping
    # def type(self, record):
    #     return {"type": "form"}
    #
    # @mapping
    # def acquirer_id(self, record):
    #     pass
    #     # yigit elle map et
    #

    #

    #
    # @mapping
    # def partner_country_id(self, record):
    #     binder = self.binder_for("odoo.res.country")
    #     return {
    #         "partner_country_id": binder.to_external(
    #             record.partner_country_id, wrap=True
    #         ),
    #     }
    #
    # @mapping
    # def sale_order_ids(self, record):
    #     binder = self.binder_for("odoo.sale.order")
    #     return {
    #         "sale_order_ids": [(6, 0, binder.to_external(record.sale_order_ids))],
    #     }
    #
    # @mapping
    # def payment_id(self, record):
    #     pass


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
