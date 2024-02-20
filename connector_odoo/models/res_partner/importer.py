# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging
import secrets
import string
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
            self._import_record(external_id, force=force)


class PartnerImportMapper(Component):
    _name = "odoo.res.partner.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.res.partner"]

    direct = [
        ("name", "name"),
        ("street", "street"),
        ("street2", "street2"),
        ("city", "city"),
        ("zip", "zip"),
        ("phone", "phone"),
        ("mobile", "mobile"),
        # ("email", "email"),
        ("website", "website"),
        ("lang", "lang"),
        ("ref", "ref"),
        ("type", "type"),
        ("comment", "comment"),
        ("ranking", "ranking"),
        ("company_type", "company_type"),
        ("sale_warn", "sale_warn"),
        ("sale_warn_msg", "sale_warn_msg"),
        ("vat", "vat"),
        ("tax_office_name", "tax_office_name"),
    ]

    @mapping
    def active(self, record):
        active = record.get("active", False)
        if not active and record.get("email"):
            # If the partner is not active, check if there is a user with the same email
            # set the partner as always active.
            user = self.env["res.users"].search([("login", "=", record["email"])])
            if user:
                active = True
        return {"active": active}

    @mapping
    def pricelist_id(self, record):
        vals = {
            "property_product_pricelist": False,
            "website_pricelist_id": False,
        }
        binder = self.binder_for("odoo.product.pricelist")
        if property_pricelist := record["property_product_pricelist"]:
            local_pricelist = binder.to_internal(property_pricelist[0], unwrap=True)
            if local_pricelist:
                vals["property_product_pricelist"] = local_pricelist.id

        if website_pricelist := record["website_pricelist_id"]:
            local_pricelist = binder.to_internal(website_pricelist[0], unwrap=True)
            if local_pricelist:
                vals["website_pricelist_id"] = local_pricelist.id

        return vals

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
                "|",
                ("active", "=", False),
                ("active", "=", True),
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
        vals = {
            "neighbour_id": False,
            "region_id": False,
            "district_id": False,
            "state_id": False,
        }
        if neighbour := record.get("neighbour_id"):
            local_neighbour = self.binder_for("odoo.address.neighbour").to_internal(
                neighbour[0], unwrap=True
            )
            if local_neighbour:
                vals["neighbour_id"] = local_neighbour.id
                vals["region_id"] = local_neighbour.region_id.id
                vals["district_id"] = local_neighbour.region_id.district_id.id
                vals["state_id"] = local_neighbour.region_id.district_id.state_id.id
        return vals

    @mapping
    def email(self, record):
        """Get the first email address"""
        vals = {"email": False}
        if record.get("email"):
            vals["email"] = record["email"].split(",")[0]
        return vals

    @mapping
    def country_id(self, record):
        vals = {"country_id": False}
        if country_id := record.get("country_id"):
            vals["country_id"] = country_id[0]
        return vals

    @mapping
    def state_id(self, record):
        vals = {"state_id": False}
        if not record.get("state_id"):
            return vals
        else:
            external_state_id = self.work.odoo_api.browse(
                model="res.country.state", res_id=record["state_id"][0]
            )

            local_state_id = self.env["res.country.state"].search(
                [
                    ("name", "=", external_state_id["name"]),
                    ("country_id.name", "=", external_state_id["country_id"][1]),
                ]
            )
            if local_state_id:
                vals["state_id"] = local_state_id.id
        return vals

    @mapping
    def parent_id(self, record):
        vals = {"parent_id": False}
        if record.get("parent_id"):
            binder = self.binder_for("odoo.res.partner")
            vals["parent_id"] = binder.to_internal(
                record["parent_id"][0], unwrap=True
            ).id
        return vals

    @mapping
    def property_account_receivable(self, record):
        vals = {"property_account_receivable_id": False}
        if account_id := record.get("property_account_receivable_id"):
            binder = self.binder_for("odoo.account.account")
            local_account = binder.to_internal(account_id[0], unwrap=True)
            if local_account:
                vals["property_account_receivable_id"] = local_account.id
        return vals

    @mapping
    def property_account_payable(self, record):
        vals = {"property_account_payable_id": False}
        if account_id := record.get("property_account_payable_id"):
            binder = self.binder_for("odoo.account.account")
            local_account = binder.to_internal(account_id[0], unwrap=True)
            if local_account:
                vals["property_account_payable_id"] = local_account.id
        return vals

    @mapping
    def utm(self, record):
        vals = {
            "campaign_id": False,
            "medium_id": False,
            "source_id": False,
        }
        if utm_campaign_id := record.get("campaign_id"):
            binder = self.binder_for("odoo.utm.campaign")
            local_campaign = binder.to_internal(utm_campaign_id[0], unwrap=True)
            if local_campaign:
                vals["campaign_id"] = local_campaign.id
        if utm_medium_id := record.get("medium_id"):
            binder = self.binder_for("odoo.utm.medium")
            local_medium = binder.to_internal(utm_medium_id[0], unwrap=True)
            if local_medium:
                vals["medium_id"] = local_medium.id
        if utm_source_id := record.get("source_id"):
            binder = self.binder_for("odoo.utm.source")
            local_source = binder.to_internal(utm_source_id[0], unwrap=True)
            if local_source:
                vals["source_id"] = local_source.id
        return vals


class PartnerImporter(Component):
    _name = "odoo.res.partner.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.res.partner"]

    def _get_context(self):
        ctx = super(PartnerImporter, self)._get_context()
        ctx["no_vat_validation"] = True
        return ctx

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        # import parent
        _logger.info("Importing dependencies for external ID %s", self.external_id)
        if parent_id := self.odoo_record["parent_id"]:
            _logger.info("Importing parent")
            self._import_dependency(parent_id[0], "odoo.res.partner", force=force)

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

        # Pricelist dependencies
        if property_pricelist := self.odoo_record["property_product_pricelist"]:
            _logger.info("Importing pricelist")
            self._import_dependency(
                property_pricelist[0],
                "odoo.product.pricelist",
                force=force,
            )
        if website_pricelist := self.odoo_record["website_pricelist_id"]:
            _logger.info("Importing website pricelist")
            self._import_dependency(
                website_pricelist[0],
                "odoo.product.pricelist",
                force=force,
            )

        result = super()._import_dependencies(force=force)
        _logger.info("Dependencies imported for external ID %s", self.external_id)
        return result

    def _after_import(self, binding, force=False):
        res = super()._after_import(binding, force)
        imported_partner = self.binder.to_internal(self.external_id)
        if not imported_partner:
            return res

        if imported_partner.type == "delivery":
            return res

        def generate_password(length=15):
            alphabet = string.ascii_letters + string.digits
            password = "".join(secrets.choice(alphabet) for i in range(length))
            return password

        # Eğer no_reset_password=True olmazsa, kullanıcılar için şifre yenileme maili gider.
        ResUsers = self.env["res.users"].with_context(no_reset_password=True)
        user = ResUsers.search([("login", "=", imported_partner.email)], limit=1)

        # Eğer kullanıcı varsa, oluşturduğumuz partner'ın şirketiyle eşleştir.
        if user:
            if (
                imported_partner.odoo_id.commercial_partner_id
                != imported_partner.odoo_id
            ):
                user.parent_id = imported_partner.odoo_id.commercial_partner_id
            return res
        else:
            ResUsers.create(
                {
                    "partner_id": imported_partner.odoo_id.id,
                    "login": imported_partner.email,
                    "name": imported_partner.name,
                    "password": generate_password(),
                    "groups_id": [(6, 0, [self.env.ref("base.group_portal").id])],
                    "lang": imported_partner.lang,
                }
            )
        return res
