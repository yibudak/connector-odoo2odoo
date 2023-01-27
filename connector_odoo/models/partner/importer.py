# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping

_logger = logging.getLogger(__name__)


def get_address_fields_from_record(env, record):
    """
    Return a dict with the address fields of the record.
    """
    # Todo : address fields should be different models
    vals = {}
    local_country_id = env["res.country"]
    local_state_id = env["res.country.state"]
    local_neighbour_id = env["address.neighbour"]
    partner_neighbour_id = record.neighbour_id

    if partner_neighbour_id:
        local_neighbour_id = env["address.neighbour"].search(
            [
                ("name", "ilike", partner_neighbour_id.name),
                ("region_id.name", "ilike", partner_neighbour_id.region_id.name),
                (
                    "region_id.district_id.name",
                    "ilike",
                    partner_neighbour_id.region_id.district_id.name,
                ),
            ]
        )
    else:
        local_state_id = env["res.country.state"].search(
            [
                ("name", "ilike", record.state_id.name),
                ("country_id.code", "ilike", record.country_id.code),
            ]
        )
    if local_neighbour_id:
        vals.update(
            {
                "zip": local_neighbour_id.code,
                "neighbour_id": local_neighbour_id.id or False,
                "region_id": local_neighbour_id.region_id.id or False,
                "district_id": local_neighbour_id.district_id.id or False,
                "state_id": local_neighbour_id.state_id.id or local_state_id.id,
                "country_id": local_neighbour_id.state_id.country_id.id
                or local_country_id.id,
            }
        )
    return vals


class PartnerBatchImporter(Component):
    """Import the Odoo Partner.

    For every partner in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.res.partner.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.res.partner"]

    def run(self, filters=None, force=False):
        """Run the synchronization"""
        external_ids = self.backend_adapter.search(filters)
        _logger.info(
            "search for odoo partner %s returned %s items", filters, len(external_ids)
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options)


class PartnerImportMapper(Component):
    _name = "odoo.res.partner.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.res.partner"]

    # TODO :     special_price => minimal_price
    direct = [
        ("name", "name"),
        ("street", "street"),
        ("street2", "street2"),
        ("city", "city"),
        ("zip", "zip"),
        ("phone", "phone"),
        ("mobile", "mobile"),
        ("email", "email"),
        ("website", "website"),
        ("lang", "lang"),
        ("ref", "ref"),
        ("comment", "comment"),
        ("company_type", "company_type"),
        ("sale_warn", "sale_warn"),
        ("sale_warn_msg", "sale_warn_msg"),
        ("vat", "vat"),
        ("tax_office_name", "tax_office_name"),
        # Todo : buraya v12 deki eklediğimiz özel fieldları da koy
    ]

    @mapping
    def category_id(self, record):
        if record.category_id:
            binder = self.binder_for("odoo.res.partner.category")
            return {
                "category_id": [
                    (
                        6,
                        0,
                        [
                            binder.to_internal(category_id, unwrap=True).id
                            for category_id in record.category_id.ids
                        ],
                    )
                ]
            }

    @mapping
    def address_fields(self, record):
        return get_address_fields_from_record(self.env, record)

    @mapping
    def parent_id(self, record):
        if record.parent_id:
            binder = self.binder_for("odoo.res.partner")
            return {
                "parent_id": binder.to_internal(record.parent_id.id, unwrap=True).id
            }

    @mapping
    def customer(self, record):
        if self.backend_record.version in (
            "11.0",
            "12.0",
        ):
            return {"customer_rank": record.customer}
        else:
            return {"customer_rank": record.customer_rank}

    @mapping
    def supplier(self, record):
        if self.backend_record.version in ("11.0", "12.0"):
            return {"supplier_rank": record.supplier}
        else:
            return {"supplier_rank": record.supplier_rank}

    @mapping
    def image(self, record):
        if self.backend_record.version in ("11.0", "12.0"):
            return {"image_1920": record.image if hasattr(record, "image") else False}
        else:
            return {"image_1920": record.image_1920}

    @mapping
    def user_id(self, record):
        if record.user_id:
            binder = self.binder_for("odoo.res.users")
            user = binder.to_internal(record.user_id.id, unwrap=True)
            return {"user_id": user.id}

    @mapping
    def property_account_payable(self, record):
        property_account_payable_id = record.property_account_payable_id
        if property_account_payable_id:
            binder = self.binder_for("odoo.account.account")
            account = binder.to_internal(property_account_payable_id.id, unwrap=True)
            if account:
                return {"property_account_payable_id": account.id}

    @mapping
    def property_account_receivable(self, record):
        property_account_receivable_id = record.property_account_receivable_id
        if property_account_receivable_id:
            binder = self.binder_for("odoo.account.account")
            account = binder.to_internal(property_account_receivable_id.id, unwrap=True)
            if account:
                return {"property_account_receivable_id": account.id}

    # @mapping
    # def property_purchase_currency_id(self, record):
    #     property_purchase_currency_id = None
    #     if hasattr(record, "property_purchase_currency_id"):
    #         property_purchase_currency_id = record.property_purchase_currency_id
    #     if not property_purchase_currency_id:
    #         if (
    #             record.property_product_pricelist_purchase
    #             and record.property_product_pricelist_purchase.currency_id
    #         ):
    #             property_purchase_currency_id = (
    #                 record.property_product_pricelist_purchase.currency_id
    #             )
    #     if property_purchase_currency_id:
    #         binder = self.binder_for("odoo.res.currency")
    #         currency = binder.to_internal(property_purchase_currency_id.id, unwrap=True)
    #         if currency:
    #             return {"property_purchase_currency_id": currency.id}


class PartnerImporter(Component):
    _name = "odoo.res.partner.importer"
    _inherit = "odoo.importer"
    _inherits = "AbstractModel"
    _apply_on = ["odoo.res.partner"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        # import parent
        _logger.info("Importing dependencies for external ID %s", self.external_id)
        if self.odoo_record.parent_id:
            _logger.info("Importing parent")
            self._import_dependency(
                self.odoo_record.parent_id.id, "odoo.res.partner", force=force
            )

        if self.odoo_record.user_id:
            _logger.info("Importing user")
            self._import_dependency(
                self.odoo_record.user_id.id, "odoo.res.users", force=force
            )

        _logger.info("Importing categories")
        for category_id in self.odoo_record.category_id:
            self._import_dependency(
                category_id.id, "odoo.res.partner.category", force=force
            )

        if self.odoo_record.property_account_payable_id:
            _logger.info("Importing account payable")
            self._import_dependency(
                self.odoo_record.property_account_payable_id.id,
                "odoo.account.account",
                force=force,
            )

        if self.odoo_record.property_account_receivable_id:
            _logger.info("Importing account receivable")
            self._import_dependency(
                self.odoo_record.property_account_receivable_id.id,
                "odoo.account.account",
                force=force,
            )

        # if (
        #     hasattr(self.odoo_record, "property_purchase_currency_id")
        #     and self.odoo_record.property_purchase_currency_id
        # ):
        #     _logger.info("Importing supplier currency")
        #     self._import_dependency(
        #         self.odoo_record.property_purchase_currency_id.id,
        #         "odoo.res.currency",
        #         force=force,
        #     )
        #
        # if (
        #     self.odoo_record.property_product_pricelist_purchase
        #     and self.odoo_record.property_product_pricelist_purchase.currency_id
        # ):
        #     _logger.info("Importing supplier currency")
        #     self._import_dependency(
        #         self.odoo_record.property_product_pricelist_purchase.currency_id.id,
        #         "odoo.res.currency",
        #         force=force,
        #     )

        result = super()._import_dependencies(force=force)
        _logger.info("Dependencies imported for external ID %s", self.external_id)
        return result

    def _after_import(self, binding, force=False):
        if self.backend_record.version == "6.1":
            _logger.info(
                "OpenERP detected, importing adresses for external ID %s",
                self.external_id,
            )
            self.env["odoo.res.partner.address.disappeared"].with_delay().import_record(
                self.backend_record, self.external_id
            )
        return super()._after_import(binding, force)
