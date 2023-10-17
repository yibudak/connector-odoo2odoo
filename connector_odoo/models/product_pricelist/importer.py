# Copyright 2013-2017 Camptocamp SA
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create
from odoo.addons.connector.exception import MappingError

_logger = logging.getLogger(__name__)


class ProductPricelistBatchImporter(Component):
    """Import the Odoo Product Pricelists.

    For every product pricelist in the list, a delayed job is created.
    A priority is set on the jobs according to their level to rise the
    chance to have the top level pricelist imported first.
    """

    _name = "odoo.product.pricelist.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.product.pricelist"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        updated_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo product pricelist %s returned %s items",
            domain,
            len(updated_ids),
        )
        for pricelist in updated_ids:
            self._import_record(pricelist, force=force)


class ProductPricelistImporter(Component):
    _name = "odoo.product.pricelist.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.pricelist"]

    def _get_binding_with_data(self, binding):
        """Return a binding with the data from the backend"""
        if not binding:
            binding = self.env["odoo.product.pricelist"].search(
                [
                    ("name", "=", self.odoo_record["name"]),
                    ("currency_id.name", "=", self.odoo_record["currency_id"][1]),
                ],
                limit=1,
            )
        return binding


class ProductPricelistImportMapper(Component):
    _name = "odoo.product.pricelist.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.product.pricelist"

    direct = [
        ("active", "active"),
        ("discount_policy", "discount_policy"),
        ("name", "name"),
        ("sequence", "sequence"),
    ]

    @only_create
    @mapping
    def check_product_pricelist_exists(self, record):
        # TODO: Improve the matching on name and position in the tree so that
        # multiple pricelist with the same name will be allowed and not
        # duplicated
        res = {}
        pricelist = self.env["product.pricelist"].search(
            [
                ("name", "=", record["name"]),
                ("currency_id.name", "=", record["currency_id"][1]),
            ],
            limit=1,
        )
        if len(pricelist) == 1:
            _logger.info(
                "found pricelist %s for record %s" % (pricelist.name, record["name"])
            )
            res.update({"odoo_id": pricelist.id})
        return {}

    @mapping
    def currency_id(self, record):
        res = {}
        currency_id = record["currency_id"]

        binder = self.binder_for("odoo.res.currency")
        if local_currency_id := binder.to_internal(currency_id[0], unwrap=True):
            _logger.info(
                "found currency %s for record %s"
                % (local_currency_id.name, record["name"])
            )
            res.update({"currency_id": local_currency_id.id})
            return res
        raise MappingError("No currency found %s" % local_currency_id.name)

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}


class ProductPricelistItemBatchImporter(Component):
    """Import the Odoo Product Pricelist Items.

    For every pricelist item in the list, a delayed job is created.
    """

    _name = "odoo.product.pricelist.item.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.product.pricelist.item"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""
        updated_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo product pricelist item %s returned %s items",
            domain,
            len(updated_ids),
        )
        for pricelist in updated_ids:
            self._import_record(pricelist, force=force)


class ProductPricelistItemImporter(Component):
    _name = "odoo.product.pricelist.item.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.pricelist.item"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        # pricelist_id is must have
        self._import_dependency(
            record["pricelist_id"][0], "odoo.product.pricelist", force=force
        )
        if product_id := record.get("product_id"):
            self._import_dependency(product_id[0], "odoo.product.product", force=force)
        if tmpl_id := record.get("product_tmpl_id"):
            self._import_dependency(tmpl_id[0], "odoo.product.template", force=force)
        if categ_id := record.get("categ_id"):
            self._import_dependency(categ_id[0], "odoo.product.category", force=force)
        if base_pricelist_id := record.get("base_pricelist_id"):
            self._import_dependency(
                base_pricelist_id[0], "odoo.product.pricelist", force=force
            )


class ProductPricelistItemImportMapper(Component):
    _name = "odoo.product.pricelist.item.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.product.pricelist.item"

    direct = [
        ("applied_on", "applied_on"),
        ("compute_price", "compute_price"),
        ("date_end", "date_end"),
        ("date_start", "date_start"),
        ("fixed_price", "fixed_price"),
        ("min_quantity", "min_quantity"),
        ("name", "name"),
        ("percent_price", "percent_price"),
        ("price", "price"),
        ("price_discount", "price_discount"),
        ("price_max_margin", "price_max_margin"),
        ("price_min_margin", "price_min_margin"),
        ("price_round", "price_round"),
        ("price_surcharge", "price_surcharge"),
    ]

    @mapping
    def pricelist_id(self, record):
        res = {"pricelist_id": False}
        if pricelist_id := record.get("pricelist_id"):
            binder = self.binder_for("odoo.product.pricelist")
            local_pricelist = binder.to_internal(pricelist_id[0], unwrap=True)
            if not local_pricelist:
                raise MappingError("No pricelist found for %s" % record["pricelist_id"])
            res.update({"pricelist_id": local_pricelist.id})
        return res

    @mapping
    def categ_id(self, record):
        res = {"categ_id": False}
        if categ_id := record.get("categ_id"):
            binder = self.binder_for("odoo.product.category")
            local_categ_id = binder.to_internal(categ_id[0], unwrap=True)
            res.update({"categ_id": local_categ_id.id})
        return res

    @mapping
    def base_pricelist_id(self, record):
        res = {}
        if base_pricelist_id := record.get("base_pricelist_id"):
            binder = self.binder_for("odoo.product.pricelist")
            local_pricelist = binder.to_internal(base_pricelist_id[0], unwrap=True)
            res.update({"base_pricelist_id": local_pricelist.id})
        return res

    @mapping
    def base(self, record):
        res = {}
        base = record["base"]
        if base == "-1":
            pricelist_base = "pricelist"
        elif base == "list_price":
            pricelist_base = "standard_price"
        else:
            pricelist_base = "sale_price"
        res.update({"base": pricelist_base})
        return res

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}

    @mapping
    def product_id(self, record):
        res = {}
        if product_id := record.get("product_id"):
            binder = self.binder_for("odoo.product.product")
            if local_product := binder.to_internal(product_id[0], unwrap=True):
                res.update({"product_id": local_product.id})
        return res

    @mapping
    def product_tmpl_id(self, record):
        res = {}
        if tmpl_id := record.get("base_pricelist_id"):
            binder = self.binder_for("odoo.product.template")
            if local_product := binder.to_internal(tmpl_id[0], unwrap=True):
                res.update({"product_tmpl_id": local_product.id})
        return res
