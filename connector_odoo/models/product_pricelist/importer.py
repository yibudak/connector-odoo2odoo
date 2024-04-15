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

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record

        if alternate_pricelist_id := record.get("alternate_pricelist_id"):
            self._import_dependency(
                alternate_pricelist_id[0], "odoo.product.pricelist", force=force
            )


class ProductPricelistImportMapper(Component):
    _name = "odoo.product.pricelist.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = "odoo.product.pricelist"

    direct = [
        ("active", "active"),
        ("discount_policy", "discount_policy"),
        ("name", "name"),
        ("sequence", "sequence"),
        ("allow_check_stock", "allow_check_stock"),
    ]

    @mapping
    def currency_id(self, record):
        if not (currency_id := record.get("currency_id")):
            return {"currency_id": False}
        currency = self.env["res.currency"].search([("name", "=", currency_id[1])])
        if len(currency) == 1:
            _logger.info(
                "found currency %s for record %s" % (currency.name, record["name"])
            )
            return {"currency_id": currency.id}
        raise MappingError("No currency found %s" % currency.name)

    @mapping
    def alternate_pricelist_id(self, record):
        vals = {"alternate_pricelist_id": False}
        if alternate_pricelist_id := record.get("alternate_pricelist_id"):
            binder = self.binder_for("odoo.product.pricelist")
            pricelist = binder.to_internal(alternate_pricelist_id[0], unwrap=True)
            vals["alternate_pricelist_id"] = pricelist.id
        return vals

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

    # Todo: this is temporary solution for price.type
    @mapping
    def price_type_currency_id(self, record):
        vals = {"price_type_currency_id": 2}
        try:
            price_type = self.work.odoo_api.browse(
                model="product.price.type", res_id=int(record["base"])
            )
            vals["price_type_currency_id"] = price_type["currency"][0]
        except:
            pass
        return vals

    @mapping
    def pricelist_id(self, record):
        binder = self.binder_for("odoo.product.pricelist")
        pricelist = binder.to_internal(record["pricelist_id"][0], unwrap=True)
        if not pricelist:
            raise MappingError("No pricelist found for %s" % record["pricelist_id"])
        return {"pricelist_id": pricelist.id}

    @mapping
    def categ_id(self, record):
        vals = {"categ_id": False}
        if categ_id := record.get("categ_id"):
            binder = self.binder_for("odoo.product.category")
            categ = binder.to_internal(categ_id[0], unwrap=True)
            vals["categ_id"] = categ.id
        return vals

    @mapping
    def base_pricelist_id(self, record):
        vals = {"base_pricelist_id": False}
        if base_pricelist_id := record.get("base_pricelist_id"):
            binder = self.binder_for("odoo.product.pricelist")
            pricelist = binder.to_internal(base_pricelist_id[0], unwrap=True)
            vals["base_pricelist_id"] = pricelist.id
        return vals

    @mapping
    def base(self, record):
        base = record.get("base")
        if base == "-1":
            pricelist_base = "pricelist"
        elif base == "list_price":
            pricelist_base = "standard_price"
        else:
            pricelist_base = "sale_price"
        return {"base": pricelist_base}

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}

    @mapping
    def product_id(self, record):
        if product_id := record.get("product_id"):
            binder = self.binder_for("odoo.product.product")
            product = binder.to_internal(product_id[0], unwrap=True)
            return {"product_id": product.id}
        return {"product_id": False}

    @mapping
    def product_tmpl_id(self, record):
        if tmpl_id := record.get("product_tmpl_id"):
            binder = self.binder_for("odoo.product.template")
            product = binder.to_internal(tmpl_id[0], unwrap=True)
            return {"product_tmpl_id": product.id}
        return {"product_tmpl_id": False}
