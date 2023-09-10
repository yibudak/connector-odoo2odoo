# Copyright 2013-2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import ast
import logging

from odoo.addons.component.core import Component
from odoo.exceptions import ValidationError
from odoo.addons.connector.components.mapper import mapping, only_create

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
            job_options = {"max_retries": 0, "priority": 15}
            self._export_record(partner, job_options=job_options)


class OdooPartnerExporter(Component):
    _name = "odoo.res.partner.exporter"
    _inherit = "odoo.exporter"
    _apply_on = ["odoo.res.partner"]

    def _has_to_skip(self):
        if not self.binding.ecommerce_partner:
            return True
        else:
            return False

    def _before_export(self):
        """Try to match parent partner from Odoo backend."""
        if not self.binding.vat or self.binding.parent_id:
            return False
        match_domain = [
            ("vat", "=", self.binding.vat),
            ("parent_id", "=", False),
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
            if self.binding.type == "other":
                self.binding.parent_id = parent
            else:
                self.binding.commercial_partner_id = parent

        return True

    def _export_dependencies(self):
        if not self.binding.parent_id:
            return
        parents = self.binding.parent_id.bind_ids

        if parents:
            parent = parents.filtered(lambda c: c.backend_id == self.backend_record)
            self._export_dependency(parent, "odoo.res.partner")

    def _create_data(self, map_record, fields=None, **kwargs):
        """Get the data to pass to :py:meth:`_create`"""
        datas = map_record.values(for_create=True, fields=fields, **kwargs)
        return datas

    def _get_external_id_with_data(self):
        """Return the external id of the record"""
        if not self.binding.vat:
            return False

        domain = [
            ("vat", "=", self.binding.vat),
            "|",
            ("name", "ilike", self.binding.name),
            ("email", "=", self.binding.email),
        ]
        # Müşterinin alt adreslerinden biriyse bu durum çalışır.
        if self.binding.parent_id:
            parent_ext_id = self.binding.mapped("parent_id.bind_ids.external_id")
            if not parent_ext_id:
                raise ValidationError(
                    "Parent partner %s not found in Odoo. Export it first."
                    % self.binding.parent_id.name
                )
            domain += [("parent_id", "=", parent_ext_id)]
        # Müşteri gerçek bir kişi olarak üye olup sipariş geçtiyse ve bu müşteri
        # bir şirkete bağlıysa bu durum çalışır.
        elif (
            self.binding.commercial_partner_id
            and self.binding.commercial_partner_id != self.binding.odoo_id
        ):
            parent_ext_id = (
                self.binding.commercial_partner_id.bind_ids.external_id
                or self.backend_adapter.search(
                    model="res.partner",
                    domain=[
                        ("parent_id", "=", False),
                        ("vat", "=", self.binding.commercial_partner_id.vat),
                    ],
                )
            )
            if not parent_ext_id:
                raise ValidationError(
                    "Parent partner %s not found in Odoo"
                    % self.binding.commercial_partner_id.name
                )
            domain += [("parent_id", "=", parent_ext_id)]

        external_ids = self.backend_adapter.search(model="res.partner", domain=domain)
        if external_ids:
            self.external_id = external_ids[0]
        return self.external_id


class PartnerExportMapper(Component):
    _name = "odoo.res.partner.export.mapper"
    _inherit = "odoo.export.mapper"
    _apply_on = ["odoo.res.partner"]

    direct = [
        ("name", "name"),
        ("street", "street"),
        ("street2", "street2"),
        ("city", "city"),
        ("website", "website"),
        ("phone", "phone"),
        ("mobile", "mobile"),
        ("email", "email"),
        ("vat", "vat"),
        ("type", "type"),
        ("ecommerce_partner", "ecommerce_partner"),
    ]

    # @mapping
    # def customer(self, record):
    #     return {"customer": True}

    @mapping
    def parent_id(self, record):
        if record.parent_id:
            binder = self.binder_for("odoo.res.partner")
            return {"parent_id": binder.to_external(record.parent_id, wrap=True)}

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

    @only_create
    @mapping
    def customer_type_and_parent_id(self, record):
        # If partner has any parent partner on current backend
        vals = {"customer_type": "person"}
        if record.parent_id:
            binder = self.binder_for("odoo.res.partner")
            parent_id = binder.to_external(record.parent_id, wrap=True)
            vals["parent_id"] = parent_id
            vals["customer_type"] = "company"
        return vals
