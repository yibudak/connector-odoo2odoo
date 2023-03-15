# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo.tools import config
from odoo.addons.connector_odoo.components.backend_adapter import OdooAPI, OdooLocation
from odoo.addons.connector_odoo.components.legacy_adapter import LegacyOdooAPI


class OdooConnector2(object):
    __slots__ = (
        "_odoo_api",
        "_legacy_odoo_api",
        "host",
        "port",
        "dbname",
        "username",
        "password",
        "lang",
    )

    def __init__(self):
        self.host = config["odoo_host"]
        self.port = config["odoo_port"]
        self.dbname = config["odoo_dbname"]
        self.username = config["odoo_login"]
        self.password = config["odoo_passwd"]
        self.lang = config["odoo_lang"]
        self._odoo_api = self._get_odoo_api()
        self._legacy_odoo_api = self._get_legacy_odoo_api()

    @property
    def odoo_api(self):
        if getattr(self, "_odoo_api", None) is None:
            self._odoo_api = self._get_odoo_api()
        return self._odoo_api

    @property
    def legacy_odoo_api(self):
        if getattr(self, "_legacy_odoo_api", None) is None:
            self._legacy_odoo_api = self._get_legacy_odoo_api()
        return self._legacy_odoo_api

    def _get_odoo_api(self):
        """Return a connection to the Odoo API. Need to set parameters in the
        configuration file. We should do this to avoid authentication on every RPC call"""
        try:
            odoo_location = OdooLocation(
                hostname=self.host,
                login=self.username,
                password=self.password,
                database=self.dbname,
                port=self.port,
                version=config["odoo_version"],
                protocol=config["odoo_protocol"],
                lang_id=self.lang,
            )
            odoo_api = OdooAPI(odoo_location).api
        except:
            odoo_api = None
        return odoo_api

    def _get_legacy_odoo_api(self):
        protocol = "https" if config["odoo_protocol"] == "jsonrpc+ssl" else "http"
        try:
            legacy_api = LegacyOdooAPI(
                f"{protocol}://{self.host}:{self.port}",
                self.dbname,
                self.password,
                self.username,
                self.lang,
            )
        except:
            legacy_api = None
        return legacy_api
