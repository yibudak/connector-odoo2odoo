# © 2013-2017 Guewen Baconnier,Camptocamp SA,Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.connector.exception import RetryableJobError


class OdooBinding(models.AbstractModel):
    """Abstract Model for the Bindings.

    All the models used as bindings between Magento and Odoo
    (``magento.res.partner``, ``magento.product.product``, ...) should
    ``_inherit`` it.
    """

    _name = "odoo.binding"
    _inherit = "external.binding"
    _description = "Odoo Binding (abstract)"

    # odoo_id = odoo-side id must be declared in concrete model
    backend_id = fields.Many2one(
        comodel_name="odoo.backend",
        string="Odoo Backend",
        required=True,
        ondelete="restrict",
    )
    external_id = fields.Integer(string="ID on Ext Odoo", required=False)

    _sql_constraints = [
        (
            "odoo_backend_odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A binding already exists with the same backend for this object.",
        )
    ]

    # note yigit: we don't need this anymore.
    # @property
    # def odoo_api(self):
    #     return self.backend_id.get_connection()

    @property
    def _unique_channel_name(self):
        """
        Split the jobs into nine channels to avoid deadlocks.
        We use the built-in hash function to get unique integers from the model name.
        """
        return f"root.{hash(self._name) % 9}"

    def resync(self):
        return self.delayed_import_record(
            self.backend_id, self.external_id, force=True
        )

    @api.constrains("backend_id", "external_id")
    def unique_backend_external_id(self):
        if self.external_id > 0:
            count = self.env[self._name].search_count(
                [
                    ("backend_id", "=", self.backend_id.id),
                    ("external_id", "=", self.external_id),
                    ("id", "!=", self.id),
                ]
            )
            if count > 0:
                raise ValidationError(
                    _(
                        "A binding already exists with the same backend '{name}' "
                        "for the external id {external_id} of the model {_name}"
                    ).format(self.backend_id.name, self.external_id, self._name)
                )

    @api.model
    def import_batch(self, backend, domain=None, force=False):
        """Prepare the import of records modified on Odoo"""
        if domain is None:
            domain = {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage="batch.importer")
            importer.set_lock()
            try:
                # todo: add job options for uid
                return importer.run(domain=domain, force=force or backend.force)
            except Exception:
                raise RetryableJobError(
                    "Could not import batch",
                    seconds=5,
                )

    @api.model
    def import_record(self, backend, external_id, force=False):
        """Import a Odoo record"""
        with backend.work_on(self._name) as work:
            importer = work.component(usage="record.importer")
            importer.set_lock(external_id)
            importer._connect_with_job(self._context)
            try:
                return importer.run(external_id, force=force)
            except Exception as e:
                raise RetryableJobError(
                    "Could not import record %s: \n%s" % (external_id, str(e)),
                    seconds=5,
                )

    @api.model
    def delayed_import_record(self, backend, external_id, force=False):
        return self.with_delay(channel=self._unique_channel_name).import_record(
            backend, external_id, force=force
        )

    @api.model
    def export_batch(self, backend, domain=None):
        """Prepare the import of records modified on Odoo"""
        if domain is None:
            domain = {}
        with backend.work_on(self._name) as work:
            exporter = work.component(usage="batch.exporter")
            return exporter.run(domain=domain)

    def export_record(self, backend, local_id=None, fields=None):
        """Export a record on Odoo"""
        self.ensure_one()
        with backend.work_on(self._name) as work:
            exporter = work.component(usage="record.exporter")
            return exporter.run(self)

    def export_delete_record(self, backend, external_id):
        """Delete a record on Odoo"""
        with backend.work_on(self._name) as work:
            deleter = work.component(usage="record.exporter.deleter")
            return deleter.run(external_id)
