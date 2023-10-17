import logging

from odoo.addons.component.core import Component
from odoo.addons.connector.components.mapper import mapping, only_create

_logger = logging.getLogger(__name__)


class IrAttachmentBatchImporter(Component):
    """Import the Odoo Attachment.

    For every Attachment in the list, a delayed job is created.
    Import from a date
    """

    _name = "odoo.ir.attachment.batch.importer"
    _inherit = "odoo.delayed.batch.importer"
    _apply_on = ["odoo.ir.attachment"]

    def run(self, domain=None, force=False):
        """Run the synchronization"""

        external_ids = self.backend_adapter.search(domain)
        _logger.info(
            "search for odoo Attachment %s returned %s items",
            domain,
            len(external_ids),
        )
        for external_id in external_ids:
            self._import_record(external_id, force=force)


class IrAttachmentImportMapper(Component):
    _name = "odoo.ir.attachment.import.mapper"
    _inherit = "odoo.import.mapper"
    _apply_on = ["odoo.ir.attachment"]

    direct = [
        ("datas", "datas"),
        ("db_datas", "db_datas"),
        ("name", "name"),
        ("description", "description"),
        ("type", "type"),
        ("res_model", "res_model"),
        ("res_name", "res_name"),
        ("store_fname", "store_fname"),
        ("file_size", "file_size"),
        ("index_content", "index_content"),
        ("usage", "usage"),
    ]

    @only_create
    @mapping
    def check_ir_attachment_exists(self, record):
        res = {}
        attachment_id = self.env["ir.attachment"].search(
            [("store_fname", "=", record.get("store_fname"))]
        )
        if attachment_id:
            _logger.info("Attachment found for %s : %s" % (record, attachment_id))
        if len(attachment_id) == 1:
            res.update({"odoo_id": attachment_id.id})
        return res

    @mapping
    def company_id(self, record):
        return {"company_id": self.env.user.company_id.id}

    @mapping
    def res_id(self, record):
        vals = {"res_id": False}
        if model := record.get("res_model"):
            if binder := self.binder_for("odoo.{}".format(model)):
                res_id = binder.to_internal(record.get("res_id"), unwrap=True)
                vals.update({"res_id": res_id.id})
        return vals


class IrAttachmentImporter(Component):
    _name = "odoo.ir.attachment.importer"
    _inherit = "odoo.importer"
    _apply_on = ["odoo.ir.attachment"]

    def _get_binding_with_data(self, binding):
        """Match the attachment with hashed store_fname."""
        binding = super(IrAttachmentImporter, self)._get_binding_with_data(binding)
        if not binding:
            binding = self.model.search(
                [("store_fname", "=", self.odoo_record["store_fname"])], limit=1
            )
        return binding

    # # FIXUP: We shouldn't skip the import. The record could be updated.
    # def _must_skip(
    #     self,
    # ):
    #     return self.env["ir.attachment"].search(
    #         [("store_fname", "=", self.odoo_record.store_fname)]
    #     )
    # NOTE yigit: skip etmek yerine map etmeye çalışıyoruz.
    # böylece hem duplicate kayıt oluşmuyor hem de update ediyoruz.
