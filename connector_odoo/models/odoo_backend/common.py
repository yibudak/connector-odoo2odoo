# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from contextlib import contextmanager
from datetime import datetime, timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

# pylint: disable=W7950
from odoo.addons.connector_odoo.components.odoo_api import OdooAPI

# TODO : verify if needed
IMPORT_DELTA_BUFFER = 30  # seconds

_logger = logging.getLogger(__name__)


class OdooBackend(models.Model):
    """Model for Odoo Backends"""

    _name = "odoo.backend"
    _description = "Odoo Backend"
    _inherit = "connector.backend"

    _backend_type = "odoo"

    name = fields.Char(required=True)

    @api.model
    def _select_state(self):
        """Available States for this Backend"""
        return [
            ("draft", "Draft"),
            ("checked", "Checked"),
            ("production", "In Production"),
        ]

    @api.model
    def _select_versions(self):
        """Available versions for this backend"""
        return [
            ("10.0", "Version 10.0.x"),
            ("11.0", "Version 11.0.x"),
            ("12.0", "Version 12.0.x"),
        ]

    active = fields.Boolean(default=True)
    state = fields.Selection(selection="_select_state", default="draft")
    version = fields.Selection(selection="_select_versions", required=True)
    login = fields.Char(
        string="Username / Login",
        required=True,
        help="Username in the external Odoo Backend.",
    )
    password = fields.Char(required=True)
    database = fields.Char(required=True)
    hostname = fields.Char(required=True)
    port = fields.Integer(
        required=True,
        help="For SSL, 443 is mostly the right choice",
        default=8069,
    )
    timeout = fields.Integer(
        required=True,
        default=15,
        help="Timeout in seconds for the connection to the backend",
    )

    uid = fields.Integer(
        string="User ID in the external system",
        help="""The user id that represents this system in the external
                system.""",
        default=0,
        readonly=True,
    )

    force = fields.Boolean(help="Execute import/export even if no changes in backend")
    protocol = fields.Selection(
        selection=[
            ("http", "JsonRPC"),
            ("https", "JsonRPC with SSL"),
        ],
        required=True,
        default="jsonrpc",
        help="For SSL consider changing the port to 443",
    )
    default_lang_id = fields.Many2one(
        comodel_name="res.lang", string="Default Language"
    )
    export_backend_id = fields.Integer(
        string="Backend ID in the external system",
        help="""The backend id that represents this system in the external
                system.""",
    )

    public_partner_id = fields.Many2one(
        comodel_name="res.partner",
        string="Public Partner",
        domain=["|", ("active", "=", True), ("active", "=", False)],
    )

    public_partner_external_id = fields.Integer(
        string="Partner ID in the external System",
        help="""External ID for Public website user on Odoo 12.0.""",
    )

    """
    DOMAIN FIELDS
    """

    external_product_domain_filter = fields.Char(
        string="External Product domain filter",
        default="[]",
        help="Filter in the Odoo Destination",
    )
    external_product_template_domain_filter = fields.Char(
        string="External Product domain filter",
        default="[]",
        help="Filter in the Odoo Destination",
    )

    external_bom_domain_filter = fields.Char(
        string="External BOM domain filter",
        default="[]",
        help="Filter in the Odoo Destination",
    )

    external_bom_line_domain_filter = fields.Char(
        string="External BOM Line domain filter",
        default="[]",
        help="Filter in the Odoo Destination",
    )

    """
    DATE FIELDS
    """

    import_base_models_from_date = fields.Datetime("Import base from date")
    import_product_from_date = fields.Datetime("Import products from date")
    import_base_multi_image_from_date = fields.Datetime("Import Base Multi Image Date")
    import_product_template_from_date = fields.Datetime(
        "Import product templates from date"
    )
    import_delivery_models_from_date = fields.Datetime(
        "Import delivery models from date"
    )
    import_currency_rate_from_date = fields.Datetime("Import currency rates from date")
    import_address_models_from_date = fields.Datetime("Import address models from date")
    import_partner_from_date = fields.Datetime("Import partners from date")
    import_pricelist_from_date = fields.Datetime("Import pricelists from date")
    import_account_from_date = fields.Datetime("Import Account from date")
    import_mrp_models_from_date = fields.Datetime("Import MRP models from date")

    @api.onchange("login")
    def _onchange_login(self):
        for backend in self:
            backend.write(
                {
                    "state": "draft",
                    "uid": 0,
                }
            )

    def get_default_language_code(self):
        lang = (
            self.default_lang_id.code
            or self.env.user.lang
            or self.env.context["lang"]
            or "tr_TR"
        )
        return lang

    def get_connection(self):
        self.ensure_one()
        return OdooAPI(
            base_url=self.protocol + "://" + self.hostname + ":" + str(self.port),
            db=self.database,
            login=self.login,
            password=self.password,
            timeout=self.timeout,
            uid=self.uid,
            language=self.get_default_language_code(),
        )

    # def get_legacy_connection(self):
    #     self.ensure_one()
    #     protocol = "https" if self.protocol == "jsonrpc+ssl" else "http"
    #     return LegacyOdooAPI(
    #         url=f"{protocol}://{self.hostname}:{self.port}",
    #         db=self.database,
    #         password=self.password,
    #         username=self.login,
    #         language=self.get_default_language_code(),
    #     )

    def button_check_connection(self):
        odoo_api = self.get_connection()
        odoo_api.test_connection()
        self.write({"state": "checked", "uid": odoo_api._uid})

    def button_reset_to_draft(self):
        self.ensure_one()
        self.write({"state": "draft", "uid": 0})

    @contextmanager
    def work_on(self, model_name, **kwargs):
        """
        Place the connexion here regarding the documentation
        http://odoo-connector.com/api/api_components.html\
            #odoo.addons.component.models.collection.Collection
        """
        self.ensure_one()
        lang = self.get_default_language_code()
        _conn = self.get_connection()
        _super = super(OdooBackend, self.with_context(lang=lang))
        # from the components we'll be able to do: self.work.odoo_api
        with _super.work_on(model_name, odoo_api=_conn, **kwargs) as work:
            yield work

    def synchronize_basedata(self):
        self.ensure_one()
        lang = self.get_default_language_code()
        self = self.with_context(lang=lang)
        try:
            for backend in self:
                for model_name in (
                    # Todo
                    "odoo.product.category",
                    "odoo.uom.uom",
                    "odoo.product.attribute.value",  # this gets attributes too
                    "odoo.res.currency.rate",  # this gets currencies too
                ):
                    # import directly, do not delay because this
                    # is a fast operation, a direct return is fine
                    # and it is simpler to import them sequentially
                    imported_ids = self.env[model_name].search([]).mapped("external_id")
                    # bypass already imported records since this method is manually triggered
                    self.env[model_name].with_context(lang=lang).import_batch(
                        backend, [("id", "not in", imported_ids)]
                    )
            return True
        except BaseException as e:
            _logger.error(e, exc_info=True)
            raise UserError(
                _(
                    "Check your configuration, we can't get the data. "
                    "Here is the error:\n%s"
                )
                % e
            ) from e

    def _get_backend(self):
        """
        Get the backend to use for the import. Usually we use this method
        for cron jobs that are not linked to a specific backend.
        """
        backend = self
        if not backend:
            backend = self.env["res.company"].browse(1).default_odoo_backend_id
        return backend

    def _cron_multi_import(self, models, date_field):
        """
        Multi-way to import data from Odoo with cron.
        """
        backend = self._get_backend()
        for model in models:
            next_time = self._cron_import(
                model, date_field, is_single=False, backend=backend
            )
        backend.write({date_field: next_time})
        return True

    def _cron_import(self, model_name, from_date_field, is_single=True, backend=None):
        """
        Base method to import data from Odoo with cron.
        """
        if not backend:
            backend = self._get_backend()
        # When we call this method for a single model, we pass the field name
        # Otherwise we pass the field itself to avoid time inconsistencies
        # between grouped models.
        from_date = getattr(backend, from_date_field)
        next_time = backend._import_from_date(model_name, from_date)
        if next_time and is_single:
            backend.write({from_date_field: next_time})
            return True
        else:
            return next_time

    def action_fix_product_images(self):
        """
        Action to call the multi_fix_product_images method from
        product.template model.
        """
        self.ensure_one()
        self.env["product.template"].with_delay().multi_fix_product_images()
        return True

    def action_fix_category_seo_name(self):
        self.ensure_one()
        self.env["product.public.category"].with_delay().multi_fix_category_seo_name()

    def action_fix_product_seo_name(self):
        self.ensure_one()
        self.env["product.template"].with_delay().multi_fix_product_seo_name()

    # def import_partner(self):
    #     backend = self._get_backend()
    #     backend._import_from_date("odoo.res.partner", "import_partner_from_date")
    #     return True

    def import_delivery_models(self):
        delivery_models = [
            "odoo.delivery.region",
            "odoo.delivery.price.rule",
            "odoo.delivery.carrier",
        ]
        date_field = "import_delivery_models_from_date"
        return self._cron_multi_import(models=delivery_models, date_field=date_field)

    def import_account_models(self):
        account_models = [
            "odoo.account.group",
            "odoo.account.account",
            "odoo.account.tax",
            "odoo.account.fiscal.position",
            "odoo.account.payment.term",
        ]
        date_field = "import_account_from_date"
        return self._cron_multi_import(models=account_models, date_field=date_field)

    def import_address_models(self):
        address_models = [
            "odoo.address.district",
            "odoo.address.region",
            "odoo.address.neighbour",
        ]
        date_field = "import_address_models_from_date"
        return self._cron_multi_import(models=address_models, date_field=date_field)

    def import_base_models(self):
        base_models = [
            "odoo.product.category",
            "odoo.uom.uom",
            "odoo.product.attribute",
            "odoo.product.attribute.value",
        ]
        date_field = "import_base_models_from_date"
        return self._cron_multi_import(models=base_models, date_field=date_field)

    def import_mrp_models(self):
        # todo: burası iyi çalışmıyor. bazı bom lineları kaçırıyor
        # yigit: bom satırlarını bom'dan sonra aktarma yaptık, belki çözüm olabilir
        mrp_models = [
            "odoo.mrp.bom",  # We import bom in line dependencies
            # "odoo.mrp.bom.line",
        ]
        date_field = "import_mrp_models_from_date"
        return self._cron_multi_import(models=mrp_models, date_field=date_field)

    def _get_next_import_time(self, import_start_time):
        next_time = import_start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
        return fields.Datetime.to_string(next_time)

    def _import_from_date(self, model, from_date_field):
        import_start_time = datetime.now()
        domain = [("write_date", "<", fields.Datetime.to_string(import_start_time))]
        for backend in self:
            if from_date_field:
                from_date = fields.Datetime.to_string(from_date_field)
                domain.append(
                    (
                        "write_date",
                        ">",
                        from_date,
                    )
                )
            self.env[model].with_delay().import_batch(backend, domain)
        return self._get_next_import_time(import_start_time)

    # we don't use this method.
    # def import_external_id(self, model, external_id, force, inmediate=True):
    #     model = self.env[model]
    #     if not inmediate:
    #         model = model.with_delay()
    #     for backend in self:
    #         model.import_record(backend, external_id, force)

    def _export_from_date(self, model, from_date_field):
        self.ensure_one()
        import_start_time = datetime.now()
        domain = [("write_date", "<", fields.Datetime.to_string(import_start_time))]
        for backend in self:
            from_date = backend[from_date_field]
            if from_date:
                domain.append(("write_date", ">", from_date))
            else:
                from_date = None
            self.env[model].with_delay().export_batch(backend, domain)
        next_time = import_start_time - timedelta(seconds=IMPORT_DELTA_BUFFER)
        next_time = fields.Datetime.to_string(next_time)
        self.write({from_date_field: next_time})
