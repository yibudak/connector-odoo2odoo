# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo.addons.connector.exception import IDMissingInBackend, RetryableJobError
from random import randint
import requests
import logging
import time


_logger = logging.getLogger(__name__)


class OdooAPI(object):
    """
    Yet another Odoo API client with JSON-RPC.
    """

    def __init__(
        self,
        base_url,
        db,
        login,
        password,
        timeout=15,
        uid=0,
        default_lang="tr_TR",
        translation_langs=None,
    ):
        self.base_url = base_url
        self.db = db
        self.login = login
        self.password = password
        self.timeout = timeout
        self._default_lang = default_lang
        self._translation_langs = translation_langs
        self._session = requests.Session()
        self._uid = self._get_uid() if uid == 0 else uid
        if not self._uid:
            _logger.error("OdooAPI: Authentication failed. Username: %s", self.login)

    def __repr__(self):
        return "<OdooAPI {}>".format(self.base_url)

    @property
    def query_id(self):
        return randint(1, 99999)

    def _post(self, payload):
        try:
            response = self._session.post(
                self.base_url + "/jsonrpc",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
            json_resp = response.json()
            if json_resp.get("error"):
                raise requests.HTTPError(json_resp["error"])
            return json_resp["result"] if ("result" in json_resp) else None
        except Exception as exc:
            _logger.error(exc)
            # time.sleep(5)  # wait 5 seconds before retrying
            raise RetryableJobError(
                "OdooAPI: Connection error: {}".format(exc),
                seconds=5,
            )

    def _base_payload(self):
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {},
            "id": self.query_id,
        }

    def _build_context(self, context=None):
        _ctx = {
            "lang": self._default_lang,
            "connector_request": True,
        }
        if context:
            _ctx.update(context)
        # Add translation languages to context
        if self._translation_langs:
            _ctx["translation_lang_codes"] = self._translation_langs
        return _ctx

    def _build_authenticate_payload(self):
        return [
            self.db,
            hasattr(self, "_uid") and self._uid or self.login,
            self.password,
        ]

    def _build_common_payload(self, method, kwargs=None, send_kwargs=True):
        payload = self._base_payload()
        args = self._build_authenticate_payload() + (kwargs or [])
        data = {
            "service": "common",
            "method": method,
            "args": [],
        }
        if send_kwargs:
            data["args"] = args

        payload["params"].update(data)
        return payload

    def _build_execute_kw_payload(
        self,
        kwargs=None,
    ):
        payload = self._base_payload()
        args = self._build_authenticate_payload() + (kwargs or [])
        data = {
            "service": "object",
            "method": "execute_kw",
            "args": args,
        }
        payload["params"].update(data)
        return payload

    def _get_uid(self):
        return self._post(
            self._build_common_payload(
                method="login",
            )
        )

    def test_connection(self):
        response = self._post(
            self._build_common_payload(
                method="version",
                send_kwargs=False,
            )
        )
        _logger.info("OdooAPI Connection test successful, version: %s", response)
        return True

    def create(self, model, data, context=None):
        return self._post(
            self._build_execute_kw_payload(
                kwargs=[
                    model,
                    "create",
                    [data],
                    {
                        "context": self._build_context(context=context),
                    },
                ],
            )
        )

    def search(
        self,
        model,
        domain,
        offset=0,
        fields=None,
        limit=None,
        order=None,
        context=None,
        get_passive=None,
    ):
        if get_passive:
            base_domain = ["|", ["active", "=", True], ["active", "=", False]]
        else:
            base_domain = []
        base_domain.extend(domain)
        return self._post(
            self._build_execute_kw_payload(
                kwargs=[
                    model,
                    "search_read",
                    [base_domain],
                    {
                        "fields": fields,
                        "offset": offset,
                        "limit": limit,
                        "order": order,
                        "context": self._build_context(context=context),
                    },
                ],
            )
        )

    def write(self, res_id, model, data, context=None):
        """
        Single record writes.
        """
        return self._post(
            self._build_execute_kw_payload(
                kwargs=[
                    model,
                    "write",
                    [[res_id], data],
                    {
                        "context": self._build_context(context=context),
                    },
                ],
            )
        )

    def browse(self, model, res_id, fields=None, context=None, get_passive=None):
        if get_passive:
            base_domain = ["|", ["active", "=", True], ["active", "=", False]]
        else:
            base_domain = []

        if res := self._post(
            self._build_execute_kw_payload(
                kwargs=[
                    model,
                    "search_read",
                    [base_domain + [["id", "=", res_id]]],
                    {
                        "fields": fields,
                        "context": self._build_context(context=context),
                    },
                ],
            )
        ):
            return res[0]
        else:
            raise IDMissingInBackend("ID {} not found in backend".format(res_id))

    def unlink(self, res_id):
        raise NotImplementedError

    def execute(self, model, method, args=None, context=None):
        return self._post(
            self._build_execute_kw_payload(
                kwargs=[
                    model,
                    method,
                    args or [],
                    {
                        "context": self._build_context(context=context),
                    },
                ],
            )
        )
