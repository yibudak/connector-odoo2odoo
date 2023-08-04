# Copyright 2022 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
import ast
import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class DeliveryCarrierBatchImporter(Component):
    """Import the Carriers."""

    _name = "odoo.delivery.carrier.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.delivery.carrier"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for delivery carriers %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options, force=force)


class DeliveryCarrierMapper(Component):
    _name = "odoo.delivery.carrier.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.delivery.carrier"]

    direct = [
        ("active", "active"),
        ("name", "name"),
        ("carrier_barcode_type", "carrier_barcode_type"),
        ("payment_type", "payment_type"),
        ("margin", "margin"),
        ("attach_barcode", "attach_barcode"),
        ("send_sms_customer", "send_sms_customer"),
        ("barcode_text_1", "barcode_text_1"),
        ("weight_calc_percentage", "weight_calc_percentage"),
        ("show_in_price_table", "show_in_price_table"),
        ("fuel_surcharge_percentage", "fuel_surcharge_percentage"),
        ("environment_fee_per_kg", "environment_fee_per_kg"),
        ("postal_charge_percentage", "postal_charge_percentage"),
        ("Emergency_fee_per_kg", "Emergency_fee_per_kg"),
        ("tracking_url_prefix_no_integration", "tracking_url_prefix_no_integration"),
        ("delivery_deadline_no_integration", "delivery_deadline_no_integration"),
    ]

    @mapping
    def deci_type(self, record):
        try:
            deci = str(record.deci_type)
        except ValueError:
            deci = "3000"
        return {"deci_type": deci}

    @mapping
    def currency_id(self, record):
        currency = self.env["res.currency"].search(
            [("name", "=", record.currency_id.name)]
        )
        return {"currency_id": currency.id}

    @mapping
    def delivery_type(self, record):
        if record.delivery_type == "fixed":
            delivery_type = "fixed"
        else:
            delivery_type = "base_on_rule"
        return {"delivery_type": delivery_type}

    @only_create
    @mapping
    def country_ids(self, record):
        return {"country_ids": [(6, 0, self.env.ref("base.tr").ids)]}

    @mapping
    def product_id(self, record):
        binder = self.binder_for("odoo.product.product")
        product = binder.to_internal(record.product_id.id, unwrap=True)
        return {"product_id": product.id}

    # @only_create
    # @mapping
    # def odoo_id(self, record):
    #     domain = ast.literal_eval(self.backend_record.local_user_domain_filter)
    #     if record.login or record.name:
    #         domain.extend(
    #             [
    #                 "|",
    #                 ("login", "=", record.login),
    #                 ("name", "=", record.name),
    #             ]
    #         )
    #     user = self.env["delivery.carrier"].search(domain)
    #     if len(user) == 1:
    #         return {"odoo_id": user.id}
    #     return {}
    #
    # @mapping
    # def image(self, record):
    #     return {"image_1920": record.image}


class DeliveryCarrierImporter(Component):
    _name = "odoo.delivery.carrier.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.delivery.carrier"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        super()._import_dependencies(force=force)
        record = self.odoo_record
        self._import_dependency(
            record.product_id.id, "odoo.product.product", force=force
        )
