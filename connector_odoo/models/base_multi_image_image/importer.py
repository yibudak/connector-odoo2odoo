import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class BaseMultiImageImageBatchImporter(Component):
    """Import the Odoo Base Multi Images.
    Import from a date
    """

    _name = "odoo.base_multi_image.image.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.base_multi_image.image"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        # We only want to import images that are related to products.
        domain += [["owner_model", "in", ("product.template", "product.product")]]

        external_ids = self.backend_adapter.search(
            domain, model="base_multi_image.image"
        )
        _logger.info(
            "search for odoo base multi images %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class BaseMultiImageImageMapper(Component):
    _name = "odoo.base_multi_image.image.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.base_multi_image.image"]

    direct = [
        ("sequence", "sequence"),
        ("extension", "extension"),
        ("comments", "comments"),
        ("is_published", "is_published"),
    ]

    def _get_owner(self, record):
        binder = self.binder_for("odoo.%s" % record["owner_model"])
        owner = binder.to_internal(record["owner_id"])
        return owner

    @mapping
    def name(self, record):
        owner = self._get_owner(record)
        name = record.get("name", owner.name)
        if owner:
            exist_images = self.env["base_multi_image.image"].search(
                [
                    ("owner_model", "=", owner.odoo_id._name),
                    ("owner_id", "=", owner.odoo_id.id),
                ]
            )
            # Avoid duplicate names
            # Todo: exclude the current record from the search
            if name in exist_images.mapped("name"):
                name = "%s %s" % (name, record["id"])
        return {"name": name}

    @mapping
    def owner_ref_model(self, record):
        vals = {
            "owner_model": False,
            "owner_id": False,
        }
        owner = self._get_owner(record)
        if owner:
            vals["owner_model"] = record["owner_model"]
            vals["owner_id"] = owner.odoo_id.id
        return vals

    @mapping
    def attachment_id(self, record):
        vals = {}
        if (attachment_id := record["attachment_id"]) and record["storage"] != "db":
            binder = self.binder_for("odoo.ir.attachment")
            local_attachment = binder.to_internal(attachment_id[0])
            if not local_attachment:
                external_attachment_id = self.work.odoo_api.browse(
                    model="ir.attachment", res_id=attachment_id[0]
                )

                local_attachment = self.env["odoo.ir.attachment"].search(
                    [("store_fname", "=", external_attachment_id["store_fname"])],
                    limit=1,
                )
            vals["attachment_id"] = local_attachment.odoo_id.id
        else:
            vals["attachment_id"] = False
        return vals

    @mapping
    def file_db_store(self, record):
        vals = {}
        if record["storage"] == "db" and record["file_db_store"]:
            vals["file_db_store"] = record["file_db_store"].replace("\n", "")
        else:
            vals["file_db_store"] = False
        return vals

    @mapping
    def product_variant_ids(self, record):
        vals = {}
        if variant_ids := record["product_variant_ids"]:
            binder = self.binder_for("odoo.product.product")
            variants = []
            for variant_id in variant_ids:
                variant = binder.to_internal(variant_id)
                if variant:
                    variants.append(variant.odoo_id.id)
            vals["product_variant_ids"] = [(6, 0, variants)]
        else:
            vals["product_variant_ids"] = False
        return vals

    @mapping
    def storage(self, record):
        """
        Yigit: This is a hack to fix the constraint error when importing images
        Actually we could import `storage` field with the `direct` mapping above
        but this field needs to be imported after `attachment_id` field.
        """
        return {"storage": record["storage"]}


class BaseMultiImageImageImporter(Component):
    _name = "odoo.base_multi_image.image.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.base_multi_image.image"]

    def _import_dependencies(self, force=False):
        """Import the dependencies for the record"""
        record = self.odoo_record
        if record["owner_model"] not in ("product.template", "product.product"):
            raise Exception(
                "The owner model of the image is not a product or a product template"
            )
        self._import_dependency(
            record["owner_id"], "odoo.%s" % record["owner_model"], force=force
        )
        # We need to import the attachment as well.
        if attachment := record["attachment_id"]:
            self._import_dependency(
                attachment[0],
                "odoo.ir.attachment",
                force=force,
            )
        if variant_ids := record.get("product_variant_ids"):
            for variant in variant_ids:
                self._import_dependency(
                    variant,
                    "odoo.product.product",
                    force=force,
                )
