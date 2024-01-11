# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import ast
import logging

from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
from odoo.addons.connector.components.mapper import mapping, only_create
from unicode_tr import unicode_tr

# from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class BatchPartnerExporter(Component):
    _name = "odoo.res.partner.batch.exporter"
    _inherit = "odoo.delayed.batch.exporter"
    _apply_on = ["odoo.res.partner"]
    _usage = "batch.exporter"

    def run(self, domain=None, force=False):
        loc_filter = ast.literal_eval(self.backend_record.local_partner_domain_filter)
        domain += loc_filter
        partner_ids = self.env["res.partner"].search(domain)

        o_ids = self.env["odoo.res.partner"].search(
            [("backend_id", "=", self.backend_record.id)]
        )
        o_partner_ids = self.env["res.partner"].search(
            [("id", "in", [o.odoo_id.id for o in o_ids])]
        )
        to_bind = partner_ids - o_partner_ids

        for p in to_bind:
            self.env["odoo.res.partner"].create(
                {
                    "odoo_id": p.id,
                    "external_id": 0,
                    "backend_id": self.backend_record.id,
                }
            )

        bind_ids = self.env["odoo.res.partner"].search(
            [
                ("odoo_id", "in", [p.id for p in partner_ids]),
                ("backend_id", "=", self.backend_record.id),
            ]
        )
        for partner in bind_ids:
            job_options = {"max_retries": 0}
            self._export_record(partner, job_options=job_options)


class OdooPartnerExporter(Component):
    _name = "odoo.res.partner.exporter"
    _inherit = "odoo.exporter"
    _apply_on = ["odoo.res.partner"]

    # Todo: remove matching functions

    def _must_skip(self):
        if not self.binding.ecommerce_partner:
            return True
        else:
            return False

    def _before_export(self):
        """Try to match parent partner from Odoo backend."""
        if not self.binding.vat or self.binding.parent_id:
            return False

        if self.binding.vat in ["1" * 11, "2" * 11]:
            return False

        if self.binding.country_id.code != "TR":
            return False

        match_domain = [
            ("vat", "=", self.binding.vat),
            ("parent_id", "=", False),
            ("ecommerce_partner", "=", False),
        ]
        matched_partner = self.backend_adapter.search(
            model="res.partner",
            domain=match_domain,
        )
        # If we found a match, but it's the same partner, we don't want to set
        # it as parent.
        if matched_partner and matched_partner[0] != self.binding.external_id:
            parent = self.binding.search(
                [
                    ("external_id", "=", matched_partner[0]),
                ],
                limit=1,
            ).commercial_partner_id
            if not parent:
                self.binding.import_record(
                    backend=self.backend_record,
                    external_id=matched_partner[0],
                )
                parent = self.binding.search(
                    [
                        ("external_id", "=", matched_partner[0]),
                    ],
                    limit=1,
                ).commercial_partner_id
            self.binding.parent_id = parent
            self.binding.company_name = False

        # İlk defa oluşturulan şirketlerde bu durum çalışır.
        if (
            (
                self.binding.commercial_partner_id == self.binding.odoo_id
            )  # This means it doesn't have any parent
            and not self.binding.parent_id
            and self.binding.company_name
        ):
            self.binding.odoo_id.create_company()
            self._check_created_company()

        return True

    def _check_created_company(self):
        created_company = self.binding.parent_id
        if not created_company.vat:
            raise ValidationError(
                "Created company %s must have vat number" % created_company.name
            )
        # To avoid infinite loop
        self.binding.external_id = 0
        external_company = self.backend_adapter.search(
            model="res.partner",
            domain=[
                ("vat", "=", created_company.vat),
                ("parent_id", "=", False),
                ("ecommerce_partner", "=", False),
            ],
            limit=1,
        )
        if external_company:

            external_company = self.work.odoo_api.browse(
                model="res.partner",
                res_id=external_company[0],
            )

            # Bulduğumuz şirketi import edelim.
            self.binding.import_record(
                self.backend_record, external_company["id"], force=False
            )
            imported_partner = self.env["odoo.res.partner"].search(
                [("external_id", "=", external_company["id"])], limit=1
            )
            if not imported_partner:
                raise ValidationError(
                    "Imported partner %s not found in Odoo."
                    " Are you sure about import process?" % external_company["name"]
                )
            # Bulduğumuz şirketi şu anki carinin parentı yapalım.
            self.binding.parent_id = imported_partner.odoo_id
            # Bir şirketle eşleştirebildik, oluşturduğumuz dummy şirketi çöpe at.
            created_company.unlink()
        else:
            created_company.ecommerce_partner = True
        return True

    def _export_dependencies(self):
        parents = self.binding.parent_id
        if (
            self.binding.commercial_partner_id
            and self.binding.commercial_partner_id != self.binding.odoo_id
        ):
            parents |= self.binding.commercial_partner_id
        for parent in parents:
            self._export_dependency(parent, "odoo.res.partner")
        return True

    def _create_data(self, map_record, fields=None, **kwargs):
        """Get the data to pass to :py:meth:`_create`"""
        datas = map_record.values(for_create=True, fields=fields, **kwargs)
        return datas

    def _get_external_id_with_data(self):
        """
        Match the company with vat number and return external id
        """

        # We should only match parents with vat number
        if not self.binding.vat or self.binding.parent_id:
            return False

        if self.binding.vat in ["1" * 11, "2" * 11]:
            return False

        if self.binding.country_id.code != "TR":
            return False

        domain = [
            ("vat", "=", self.binding.vat),
            ("parent_id", "=", False),
        ]
        matched_partner = self.backend_adapter.search(
            model="res.partner",
            domain=domain,
        )
        if matched_partner:
            self.external_id = matched_partner[0]
        return self.external_id


class PartnerExportMapper(Component):
    _name = "odoo.res.partner.export.mapper"
    _inherit = "odoo.export.mapper"
    _apply_on = ["odoo.res.partner"]

    direct = [
        ("street", "street"),
        ("street2", "street2"),
        ("city", "city"),
        ("website", "website"),
        ("lang", "lang"),
        ("phone", "phone"),
        ("mobile", "mobile"),
        ("email", "email"),
        ("vat", "vat"),
        ("type", "type"),
        ("ecommerce_partner", "ecommerce_partner"), # todo: remove this field
        ("tax_office_name", "tax_office_name"),
    ]

    @mapping
    def name(self, record):
        return {"name": unicode_tr(record.name).title()}

    @mapping
    def country_id(self, record):
        return {"country_id": record.country_id.id}

    @mapping
    def customer(self, record):
        return {"customer": True}

    @mapping
    def parent_id(self, record):
        vals = {"parent_id": False}
        if record.parent_id:
            binder = self.binder_for("odoo.res.partner")
            vals["parent_id"] = binder.to_external(record.parent_id, wrap=True)
        return vals

    @mapping
    def accounts(self, record):
        vals = {
            "property_account_receivable_id": False,
            "property_account_payable_id": False,
        }
        binder = self.binder_for("odoo.account.account")
        if record.property_account_receivable_id:
            vals["property_account_receivable_id"] = binder.to_external(
                record.property_account_receivable_id, wrap=True
            )
        if record.property_account_payable_id:
            vals["property_account_payable_id"] = binder.to_external(
                record.property_account_payable_id, wrap=True
            )
        return vals

    @mapping
    def pricelists(self, record):
        vals = {"property_product_pricelist": False}
        if record.property_product_pricelist:
            binder = self.binder_for("odoo.product.pricelist")
            external_pricelist = binder.to_external(
                record.property_product_pricelist, wrap=True
            )
            if external_pricelist:
                vals["property_product_pricelist"] = external_pricelist

    @mapping
    def address_fields(self, record):
        vals = {}
        adapter = self.work.odoo_api
        if record.neighbour_id:
            odoo_neighbour = self.env["odoo.address.neighbour"].search(
                [("odoo_id", "=", record.neighbour_id.id)]
            )
            if not odoo_neighbour:
                raise ValidationError(
                    "Neighbour %s not found in Odoo" % record.neighbour_id.name
                )
            remote_neighbour = adapter.browse(
                model="address.neighbour", res_id=odoo_neighbour.external_id
            )
            # We can use odoo_neighbour instead remote_neighbour
            if remote_neighbour:
                vals["neighbour_id"] = remote_neighbour["id"]
                vals["region_id"] = remote_neighbour["region_id"][0]
                vals["district_id"] = remote_neighbour["district_id"][0]
                vals["state_id"] = remote_neighbour["state_id"][0]
                # vals["country_id"] = remote_neighbour["country_id"][0]
        return vals

    # @only_create
    @mapping
    def is_company_and_parent_id(self, record):
        # If partner has any parent partner on current backend
        vals = {"is_company": record.is_company}
        if parent := (
            record.parent_id
            or (
                record.commercial_partner_id
                and record.commercial_partner_id != record.odoo_id
            )
        ):
            binder = self.binder_for("odoo.res.partner")
            parent_id = binder.to_external(parent, wrap=True)
            vals["parent_id"] = parent_id
            vals["is_company"] = False
        return vals
