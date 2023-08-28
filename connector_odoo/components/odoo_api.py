# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo.addons.connector.exception import IDMissingInBackend
from random import randint
import requests
import logging


_logger = logging.getLogger(__name__)


class OdooAPI(object):
    # todo: açıklama ekle neden bunu yaptığımızı anlat
    def __init__(
        self,
        base_url,
        db,
        login,
        password,
        model=None,  # todo: create a model class so we can execute methods on it
        timeout=15,
        uid=0,
        language="tr_TR",
    ):
        self.base_url = base_url
        self.db = db
        self.login = login
        self.password = password
        self.model = model  # todo: create a model class so we can execute methods on it
        self.timeout = timeout
        self._language = language
        self._session = requests.Session()
        if uid == 0:
            self._uid = self._get_uid()
        else:
            self._uid = uid
        if not self._uid:
            _logger.error("OdooAPI: Authentication failed. Username: %s", self.login)

    def __repr__(self):
        return "<OdooAPI {}>".format(self.base_url)

    @property
    def query_id(self):
        return randint(1, 1337)

    def _post(self, payload):
        with self._session as client:
            try:
                response = client.post(
                    self.base_url + "/jsonrpc",
                    json=payload,
                    timeout=self.timeout,
                )
                response.raise_for_status()
                json_resp = response.json()

                if json_resp.get("error"):
                    raise requests.HTTPError(json_resp["error"])

                return response.json()["result"]

            except (requests.HTTPError, KeyError) as exc:
                _logger.error(exc)
                raise exc

    def _base_payload(self):
        return {
            "jsonrpc": "2.0",
            "method": "call",
            "params": {},
            "id": self.query_id,
        }

    def _build_context(self, context=None):
        _ctx = {"lang": self._language}
        if context:
            _ctx.update(context)
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
        context=None,
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

    def create(self, model, data):
        return self._post(
            self._build_execute_kw_payload(
                kwargs=[
                    model,
                    "create",
                    [data],
                    {
                        "context": self._build_context(),
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
    ):
        return self._post(
            self._build_execute_kw_payload(
                kwargs=[
                    model,
                    "search_read",
                    [domain],
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

    def write(self, res_id, model, data):
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
                        "context": self._build_context(),
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
        pass

    def execute(self, model, method, args=None, kwargs=None, context=None):
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


# class Model(object):
#     def __init__(self, api, model):
#         self.api = api
#         self.model = model
#
#     def __call__(self, *args, **kwargs):
#         return self.search(*args, **kwargs)

# def authenticate(self):
#     self.session = httpx.Client()
#     url = self.base_url + "/web/session/authenticate"
#     data = {
#         "jsonrpc": "2.0",
#         "params": {
#             "db": self.db,
#             "login": self.username,
#             "password": self.password,
#         },
#     }
#     response = self.session.post(url, json=data)
#     response.raise_for_status()
#     return response.json()
#

# def execute_kw(self, model, method, args, kwargs):
#     url = self.base_url + "/web/dataset/call_kw/" + model + "/" + method
#     data = {
#         "jsonrpc": "2.0",
#         "params": {
#             "model": model,
#             "method": method,
#             "args": args,
#             "kwargs": kwargs,
#         },
#     }
#     response = self.session.post(url, json=data)
#     response.raise_for_status()
#     return response.json()
