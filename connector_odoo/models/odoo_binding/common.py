# © 2013-2017 Guewen Baconnier,Camptocamp SA,Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.connector.exception import RetryableJobError
from hashlib import md5
import time


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
    active_job_ids = fields.One2many(
        "queue.job",
        compute="_compute_active_job_ids",
        store=False,
    )

    _sql_constraints = [
        (
            "odoo_backend_odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A binding already exists with the same backend for this object.",
        )
    ]

    def _compute_active_job_ids(self):
        """
        Add active job ids to the recordset.
        """
        for record in self:
            if record.id and hasattr(record, "bind_ids"):
                record.active_job_ids = self.env["queue.job"].search(
                    [
                        ("odoo_binding_model_name", "=", record._name),
                        ("odoo_binding_id", "=", record.id),
                        ("state", "!=", "done"),
                    ]
                )
            else:
                record.active_job_ids = False

    @property
    def _unique_channel_name(self):
        """
        Split the jobs into nine channels to avoid deadlocks.
        Note: Do NOT use built-in hash method since it creates different hashes
        for the same string in different processes.
        Workflow:
        1. Get the md5 hash of the model name.
        2. Sum the ascii values of the hash.
        3. Get the remainder of the sum divided by 10.
        4. Return the remainder.

        .. attribute:: priority

        Priority of the job, 0 being the higher priority.
        """
        if hasattr(self, "_special_channel"):
            return self._special_channel
        md5_hash = md5(self._name.encode("utf-8")).hexdigest()
        return f"root.{sum(ord(x) for x in md5_hash) % 10}"

    @property
    def _priority(self):
        """
        Some models are more important than others. For example, we want to
        prioritize the import of partners over the import of product images.
        """
        if hasattr(self, "_queue_priority") and self._queue_priority:
            return self._queue_priority
        else:
            return 99

    def resync(self):
        return self.delayed_import_record(self.backend_id, self.external_id, force=True)

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

    """
    IMPORTERS
    """

    @api.model
    def import_batch(self, backend, domain=None, force=False):
        """Prepare the import of records modified on Odoo"""
        if domain is None:
            domain = {}
        with backend.work_on(self._name) as work:
            importer = work.component(usage="batch.importer")
            importer.set_lock()
            try:
                return importer.run(domain=domain, force=force or backend.force)
            except Exception:
                raise RetryableJobError(
                    "Could not import batch",
                    seconds=5,
                )

    @api.model
    def delayed_import_batch(self, backend, domain=None, force=None):
        return (
            self.sudo()
            .with_delay(
                channel=self._unique_channel_name,
                priority=self._priority,
            )
            .import_batch(backend, domain=domain, force=force)
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
                # Bağlantı hatalarında iş sürekli tekrar deneniyor ve delay olmadığı
                # zaman retry_count çok hızlı bir şekilde doluyor. Delay ekleyerek
                # aradaki bağlantının düzelmesini bekliyoruz.
                time.sleep(0.5)
                raise RetryableJobError(
                    "Could not import record %s: \n%s" % (external_id, str(e)),
                    seconds=5,
                )

    @api.model
    def delayed_import_record(self, backend, external_id, force=False):
        return (
            self.sudo()
            .with_delay(
                channel=self._unique_channel_name,
                priority=self._priority,
            )
            .import_record(backend, external_id, force=force)
        )

    """
    EXPORTERS
    """

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
            exporter._connect_with_job(self._context)
            return exporter.run(self)

    def delayed_export_record(self, backend, local_id=None, fields=None):
        return (
            self.sudo()
            .with_delay(
                channel=self._unique_channel_name,
                priority=self._priority,
            )
            .export_record(backend, local_id=local_id, fields=fields)
        )

    """
    EXECUTERS
    
    Note: Executer methods have lower priority than importers and exporters.
    """

    @api.model
    def delayed_execute_method(self, backend, model, method, args=None, context=None):
        return (
            self.sudo()
            .with_delay(
                channel=self._unique_channel_name,
                priority=self._priority + 50,
            )
            .execute_method(backend, model, method, args=args, context=context)
        )

    @api.model
    def execute_method(self, backend, model, method, args=None, context=None):
        """Execute a method on Odoo"""

        if backend.no_export:
            return _("Executing is disabled for this backend (no export flag)")

        odoo_api = backend.get_connection()
        # Always pass the external_id as first argument to use as ~self~
        if not args:
            if not self.external_id:
                raise RetryableJobError(
                    "This record has no external_id, cannot execute method", seconds=5
                )
            args = [self.external_id]
        return odoo_api.execute(model, method, args, context)
