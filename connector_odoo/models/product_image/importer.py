import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class ProductImageBatchImporter(Component):
    """Import the Odoo Product Attachments.

    For every Attachment in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.product.image.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.product.image"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(
            domain, model="base_multi_image.image"
        )
        _logger.info(
            "search for odoo product images %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class ProductImageImportMapper(Component):
    _name = "odoo.product.image.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.product.image"]

    direct = [
        ("image_main", "image_1920"),
        # ("name", "name"), # We need to handle missing names
        # ("name", "name"),
        # ("description", "description"),
        # ("type", "type"),
        # ("res_model", "res_model"),
        # ("res_name", "res_name"),
        # ("store_fname", "store_fname"),
        # ("file_size", "file_size"),
        # ("index_content", "index_content"),
        # ("usage", "usage"),
    ]

    @mapping
    def name(self, record):
        # todo: samet (binder model neden kullanmadık?)
        if record.name:
            return {"name": record.name}
        else:
            return {"name": "Product Image"}

    @mapping
    def product_tmpl_id(self, record):
        # todo: samet
        vals = {"product_tmpl_id": False}
        imported_tmpl_id = self.env["odoo.product.template"].search(
            [
                ("external_id", "=", record.owner_id)
            ]
        )
        if imported_tmpl_id:
            vals.update({"product_tmpl_id": imported_tmpl_id.odoo_id.id})
        return vals


class ProductImageImporter(Component):
    _name = "odoo.product.image.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.product.image"]

    def run(self, external_id, force=False):
        """Map base_multi_image.image to product.image before import"""

        self.backend_adapter._odoo_model = "base_multi_image.image"
        super(ProductImageImporter, self).run(external_id, force=force)

    # FIXUP: We shouldn't skip the import. The record could be updated.
    # def _must_skip(
    #     self,
    # ):
    #     return self.env["product.image"].search(
    #         [("store_fname", "=", self.odoo_record.store_fname)]
    #     )
