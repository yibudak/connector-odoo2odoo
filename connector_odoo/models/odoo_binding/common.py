# © 2013-2017 Guewen Baconnier,Camptocamp SA,Akretion
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from odoo.addons.connector_odoo.components.backend_adapter import OdooAPI, OdooLocation
from odoo.addons.connector_odoo.components.legacy_adapter import LegacyOdooAPI
from odoo.tools import config


def _get_api_conn():
    """Return a connection to the Odoo API. Need to set parameters in the
    configuration file. We should do this to avoid authentication on every RPC call"""
    host = config["odoo_host"]
    port = config["odoo_port"]
    dbname = config["odoo_dbname"]
    username = config["odoo_login"]
    password = config["odoo_passwd"]
    lang = config["odoo_lang"]
    try:
        odoo_location = OdooLocation(
            hostname=host,
            login=username,
            password=password,
            database=dbname,
            port=port,
            version=config["odoo_version"],
            protocol=config["odoo_protocol"],
            lang_id=lang,
        )
        connection = OdooAPI(odoo_location).api
    except:
        connection = None

    protocol = "https" if config["odoo_protocol"] == "jsonrpc+ssl" else "http"
    try:
        legacy_api = LegacyOdooAPI(
            f"{protocol}://{host}:{port}", dbname, password, username, lang
        )
    except:
        legacy_api = None
    return connection, legacy_api


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
    external_id = fields.Integer(string="ID on Ext Odoo", default=-1)

    _sql_constraints = [
        (
            "odoo_backend_odoo_uniq",
            "unique(backend_id, odoo_id)",
            "A binding already exists with the same backend for this object.",
        )
    ]

    _api_conn, _legacy_api_conn = _get_api_conn()

    @property
    def odoo_api(self):
        if getattr(self, "_api_conn", None) is None:
            self._api_conn, self._legacy_api_conn = _get_api_conn()
        return self._api_conn

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

    def resync(self):
        return self.with_delay().export_record(self.backend_id)

    def set_connectors(self, work_context):
        """This method set the connectors to the work context.
        If any connector is not set, it will be created.
        """
        # Todo: check if the connector is already set or not
        setattr(work_context, "odoo_api", self._api_conn)
        setattr(work_context, "legacy_api", self._legacy_api_conn)
        return True

    @api.model
    def import_batch(self, backend, filters=None):
        """Prepare the import of records modified on Odoo"""
        if filters is None:
            filters = {}
        with backend.work_on(self._name) as work:
            self.set_connectors(work)
            importer = work.component(usage="batch.importer")
            return importer.run(filters=filters, force=backend.force)

    @api.model
    def import_record(self, backend, external_id, force=False):
        """Import a Odoo record"""
        with backend.work_on(self._name) as work:
            self.set_connectors(work)
            importer = work.component(usage="record.importer")
            return importer.run(external_id, force=force)

    @api.model
    def import_record_legacy(self, backend, external_id, force=False):
        """Import a Odoo record"""
        with backend.work_on(self._name) as work:
            self.set_connectors(work)
            importer = work.component(usage="record.importer")
            return importer.run_legacy(external_id, force=force)

    @api.model
    def export_batch(self, backend, filters=None):
        """Prepare the import of records modified on Odoo"""
        if filters is None:
            filters = {}
        with backend.work_on(self._name) as work:
            exporter = work.component(usage="batch.exporter")
            return exporter.run(filters=filters)

    def export_record(self, backend, local_id=None, fields=None):
        """Export a record on Odoo"""
        self.ensure_one()
        with backend.work_on(self._name) as work:
            self.set_connectors(work)
            exporter = work.component(usage="record.exporter")
            return exporter.run(self)

    def export_delete_record(self, backend, external_id):
        """Delete a record on Odoo"""
        with backend.work_on(self._name) as work:
            deleter = work.component(usage="record.exporter.deleter")
            return deleter.run(external_id)
