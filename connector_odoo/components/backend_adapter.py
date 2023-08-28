# Copyright 2017 Camptocamp SA
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html)

import logging

from odoo import _
from odoo.exceptions import UserError

from odoo.addons.component.core import AbstractComponent

_logger = logging.getLogger(__name__)

try:
    import odoorpc
except ImportError:
    _logger.info("Cannot import 'odoorpc' Lib")


class OdooLocation(object):
    __slots__ = (
        "hostname",
        "login",
        "password",
        "database",
        "port",
        "version",
        "protocol",
        "timeout",
        "lang_id",
        "use_custom_api_path",
    )

    def __init__(
        self,
        hostname,
        login,
        password,
        database,
        port,
        version,
        protocol,
        timeout,
        lang_id="en_US",
        use_custom_api_path=False,
    ):
        self.hostname = hostname
        self.login = login
        self.password = password
        self.database = database
        self.port = port
        self.version = version
        self.timeout = timeout
        self.protocol = protocol
        self.lang_id = lang_id


class OdooAPI(object):
    def __init__(self, location):
        """
        :param location: Odoo location
        :type location: :class:`OdooLocation`
        """
        self._location = location
        self._api = None

    def _api_login(self, api):
        if self._location.version == "6.1":
            try:
                api.login(
                    database=self._location.database,
                    user=self._location.login,
                    passwd=self._location.password,
                )
            except odoorpc.error.RPCError as e:
                _logger.exception(e)
                raise UserError(str(e)) from e
        else:
            try:
                api.login(
                    db=self._location.database,
                    login=self._location.login,
                    password=self._location.password,
                )
            except odoorpc.error.RPCError as e:
                _logger.exception(e)
                raise UserError(e) from e

    @property
    def api(self):
        if self._api is None:
            api = odoorpc.ODOO(
                host=self._location.hostname,
                port=self._location.port,
                protocol=self._location.protocol,
                timeout=self._location.timeout,
            )
            self._api_login(api)
            self._api = api

            _logger.info("Associated lang %s to location" % self._location.lang_id)
            if self._location.lang_id:
                if self._location.version in ("6.1",):
                    self._api.context["lang"] = self._location.lang_id
                else:
                    self._api.env.context["lang"] = self._location.lang_id

            _logger.info(
                "Created a new Odoo API instance and logged In with context %s"
                % self._api.env.context
                if hasattr(self._api, "env")
                else self._api.context
            )
        return self._api

    def complete_check(self):
        api = self.api
        if not api.version.startswith(self._location.version):
            raise UserError(
                _("Server indicates version %s. Please adapt your conf")
            ) % api.version

        self._api_login(api)

    def __enter__(self):
        # we do nothing, api is lazy
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        _logger.info(traceback)


class OdooCRUDAdapter(AbstractComponent):
    """External Records Adapter for Odoo"""

    _name = "odoo.crud.adapter"
    _inherit = ["base.backend.adapter", "base.odoo.connector"]
    _usage = "backend.adapter"

    def search(self, domain=None):
        """Search records according to some criterias
        and returns a list of ids"""
        raise NotImplementedError

    # pylint: disable=W8106
    def read(self, *kwargs):
        """Returns the information of a record"""
        raise NotImplementedError

    # pylint: disable=W8106
    def search_read(self, *kwargs):
        """Search records according to some criterias
        and returns their information"""
        raise NotImplementedError

    # pylint: disable=W8106
    def create(self, *kwargs):
        """Create a record on the external system"""
        raise NotImplementedError

    # pylint: disable=W8106
    def write(self, *kwargs):
        """Update records on the external system"""
        raise NotImplementedError

    # pylint: disable=W8106
    def delete(self, *kwargs):
        """Delete a record on the external system"""
        raise NotImplementedError

    # pylint: disable=W8106
    def execute(self, *kwargs):
        """Execute method for a record on the external system"""
        raise NotImplementedError


class GenericAdapter(AbstractComponent):
    _name = "odoo.adapter"
    _inherit = "odoo.crud.adapter"

    # _odoo_model = None
    # _admin_path = None

    def search(
        self,
        domain=None,
        model=None,
        offset=0,
        limit=None,
        order=None,
        fields=None,
    ):
        """Search records according to some criterias
        and returns a list of ids
        :rtype: list
        """

        ext_model = model or self._odoo_model

        try:
            odoo_api = self.work.odoo_api
        except AttributeError:
            raise AttributeError(
                "You must provide a odoo_api attribute with a "
                "OdooAPI instance to be able to use the "
                "Backend Adapter."
            )
        # Todo: maybe we shouldn't only get id field.
        return [
            q["id"]
            for q in odoo_api.search(
                model=ext_model,
                fields=fields or ["id"],
                domain=domain or [],
                offset=offset,
                limit=limit,
                order=order,
                # Todo: add context.
            )
        ]

    # pylint: disable=W8106,W0622
    def read(self, id, model=None, context=None):
        """Returns the information of a record
        :rtype: dict
        """
        ext_model = model or self._odoo_model
        try:
            odoo_api = self.work.odoo_api
        except AttributeError:
            raise AttributeError(
                "You must provide a odoo_api attribute with a "
                "OdooAPI instance to be able to use the "
                "Backend Adapter."
            )

        return odoo_api.browse(
            model=ext_model, res_id=id, context=context, get_passive=self._get_passive
        )

    def create(self, data):
        ext_model = self._odoo_model
        try:
            odoo_api = self.work.odoo_api
        except AttributeError as e:
            raise AttributeError(
                "You must provide a odoo_api attribute with a "
                "OdooAPI instance to be able to use the "
                "Backend Adapter."
            ) from e
        return odoo_api.create(model=ext_model, data=data)

    def write(self, res_id, data):
        ext_model = self._odoo_model
        try:
            odoo_api = self.work.odoo_api
        except AttributeError as e:
            raise AttributeError(
                "You must provide a odoo_api attribute with a "
                "OdooAPI instance to be able to use the "
                "Backend Adapter."
            ) from e
        return odoo_api.write(res_id=res_id, model=ext_model, data=data)

