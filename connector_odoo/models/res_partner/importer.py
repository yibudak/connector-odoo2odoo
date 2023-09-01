# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class PartnerBatchImporter(Component):
    """Import the Odoo Partner.

    For every partner in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.res.partner.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.res.partner"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""
        external_ids = self.backend_adapter.search(domain)
        _logger.debug(
            "search for odoo partner %s returned %s items", domain, len(external_ids)
        )
        for external_id in external_ids:
            job_options = {"priority": 15}
            self._import_record(external_id, job_options=job_options)


class PartnerImportMapper(Component):
    _name = "odoo.res.partner.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.res.partner"]

    direct = [
        ("active", "active"),
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
        ("ranking", "ranking"),
        ("company_type", "company_type"),
        ("sale_warn", "sale_warn"),
        ("sale_warn_msg", "sale_warn_msg"),
        ("vat", "vat"),
        ("tax_office_name", "tax_office_name"),
        # Todo : buraya v12 deki eklediğimiz özel fieldları da koy
    ]

    # @mapping
    # def category_id(self, record):
    #     if record["category_id"]:
    #         binder = self.binder_for("odoo.res.partner.category")
    #         return {
    #             "category_id": [
    #                 (
    #                     6,
    #                     0,
    #                     [
    #                         binder.to_internal(category_id, unwrap=True).id
    #                         for category_id in record["category_id"]
    #                     ],
    #                 )
    #             ]
    #         }

    @only_create
    @mapping
    def check_res_partner_exists(self, record):
        vals = {}
        if not record.get("vat"):
            return vals

        odoo_partner_id = self.env["odoo.res.partner"].search(
            [
                ("external_id", "=", record["id"]),
                ("name", "=", record["name"]),
                ("vat", "=", record["vat"]),
            ]
        )
        if len(odoo_partner_id) == 1:
            _logger.info(
                "Res partner found for %s : %s" % (record["name"], odoo_partner_id.name)
            )
            vals.update({"odoo_id": odoo_partner_id.odoo_id.id})
        return vals

    @mapping
    def address_fields(self, record):
        vals = {}
        if neighbour := record.get("neighbour_id"):
            local_neighbour = self.binder_for("odoo.address.neighbour").to_internal(
                neighbour[0], unwrap=True
            )
            if local_neighbour:
                vals["neighbour_id"] = local_neighbour.odoo_id.id
                vals["region_id"] = local_neighbour.region_id.id
                vals["district_id"] = local_neighbour.region_id.district_id.id
                vals["state_id"] = local_neighbour.region_id.district_id.state_id.id
        return vals

    @mapping
    def country_id(self, record):
        vals = {}
        if not record.get("country_id"):
            return vals
        local_country_id = self.env["res.country"].search(
            [("name", "=", record["country_id"][1])]
        )
        if local_country_id:
            vals["country_id"] = local_country_id.id
        return vals

    @mapping
    def state_id(self, record):
        vals = {}
        if not record.get("state_id"):
            return vals
        else:
            external_state_id = self.work.odoo_api.browse(
                model="res.country.state", res_id=record["state_id"][0]
            )

            local_state_id = self.env["res.country.state"].search(
                [
                    ("name", "ilike", external_state_id["name"]),
                    ("country_id.name", "=", external_state_id["country_id"][1]),
                ]
            )
            if local_state_id:
                vals["state_id"] = local_state_id.id
        return vals

    @mapping
    def parent_id(self, record):
        vals = {}
        if record.get("parent_id"):
            binder = self.binder_for("odoo.res.partner")
            vals["parent_id"] = binder.to_internal(
                record["parent_id"][0], unwrap=True
            ).id
        return vals

    # TODO: this slows down the import. should we really import the image?
    # @mapping
    # def image(self, record):
    #     if self.backend_record.version in ("11.0", "12.0"):
    #         return {"image_1920": record.image if hasattr(record, "image") else False}
    #     else:
    #         return {"image_1920": record.image_1920}

    # @mapping
    # def user_id(self, record):
    #     if record["user_id"]:
    #         binder = self.binder_for("odoo.res.users")
    #         user = binder.to_internal(record["user_id"][0], unwrap=True)
    #         return {"user_id": user.id}

    @mapping
    def property_account_receivable(self, record):
        if account_id := record.get("property_account_payable_id"):
            binder = self.binder_for("odoo.account.account")
            local_account = binder.to_internal(account_id[0], unwrap=True)
            if local_account:
                return {"property_account_payable_id": local_account.id}

    @mapping
    def property_account_receivable(self, record):
        if account_id := record.get("property_account_receivable_id"):
            binder = self.binder_for("odoo.account.account")
            local_account = binder.to_internal(account_id[0], unwrap=True)
            if local_account:
                return {"property_account_receivable_id": local_account.id}

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
    _apply_on = ["odoo.res.partner"]
    # _import_fields = [
    #     "write_date",
    #     "id",
    #     "name",
    #     "street",
    #     "street2",
    #     "city",
    #     "zip",
    #     "phone",
    #     "mobile",
    #     "email",
    #     "website",
    #     "lang",
    #     "ref",
    #     "comment",
    #     "company_type",
    #     "sale_warn",
    #     "sale_warn_msg",
    #     "vat",
    #     "tax_office_name",
    #     "category_id",
    #     "neighbour_id",
    #     "user_id",
    #     "country_id",
    #     "state_id",
    #     "parent_id",
    #     "ranking",
    #     "property_account_payable_id",
    #     "property_account_receivable_id",
    # ]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        # import parent
        _logger.info("Importing dependencies for external ID %s", self.external_id)
        if parent_id := self.odoo_record["parent_id"]:
            _logger.info("Importing parent")
            self._import_dependency(parent_id[0], "odoo.res.partner", force=force)
        # Todo yigit: should we import users?
        # if self.odoo_record["user_id"]:
        #     _logger.info("Importing user")
        #     self._import_dependency(
        #         self.odoo_record["user_id"][0], "odoo.res.users", force=force
        #     )

        # Todo yigit: do we have partner categories in odoo?
        # _logger.info("Importing categories")
        # for category_id in self.odoo_record["category_id"]:
        #     self._import_dependency(
        #         category_id, "odoo.res.partner.category", force=force
        #     )

        if payable_account_id := self.odoo_record["property_account_payable_id"]:
            _logger.info("Importing account payable")
            self._import_dependency(
                payable_account_id[0],
                "odoo.account.account",
                force=force,
            )

        if receivable_account_id := self.odoo_record["property_account_receivable_id"]:
            _logger.info("Importing account receivable")
            self._import_dependency(
                receivable_account_id[0],
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

    # def _after_import(self, binding, force=False):
    #     if self.backend_record.version == "6.1":
    #         _logger.info(
    #             "OpenERP detected, importing adresses for external ID %s",
    #             self.external_id,
    #         )
    #     return super()._after_import(binding, force)
