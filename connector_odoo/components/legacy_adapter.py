# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
import xmlrpc.client as xmlrpclib
import datetime
import time


class LegacyOdooAPI:
    def __init__(self, url, db, password, username, language):
        self.url = url
        self.db = db
        self.password = password
        self.username = username
        self.language = language
        self.uid = 0
        self.connect_and_authenticate()
        self.models = xmlrpclib.ServerProxy(
            "{}/xmlrpc/2/object".format(self.url), allow_none=True
        )

    def connect_and_authenticate(self):
        common = xmlrpclib.ServerProxy(
            "{}/xmlrpc/2/common".format(self.url), allow_none=True
        )
        self.uid = common.authenticate(self.db, self.username, self.password, {})

    def search(self, model_name, parameter_list):
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            "search",
            parameter_list,
        )
        return res

    def search_with_pagination(self, model_name, parameter_list, pagination_dict):
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            "search",
            parameter_list,
            pagination_dict,
        )
        return res

    def search_count(self, model_name, parameter_list):
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            "search_count",
            parameter_list,
        )
        return res

    def read(self, model_name, ids, fields_dict):
        fields_dict["context"] = {"lang": self.language}
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            "read",
            [ids],
            fields_dict,
        )
        return res

    def get_fields(self, model_name, attribute_list):
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            "fields_get",
            [],
            attribute_list,
        )
        return res

    def search_read(self, model_name, parameter_list, fields_dict):
        fields_dict["context"] = {"lang": self.language}
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            "search_read",
            parameter_list,
            fields_dict,
        )
        return res

    def create(self, model_name, parameter_list):
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            "create",
            parameter_list,
        )
        return res

    def write(self, model_name, parameter_list):
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            "write",
            parameter_list,
        )
        return res

    def execute_kw(self, model_name, method, parameter_list):
        res = self.models.execute_kw(
            self.db,
            self.uid,
            self.password,
            model_name,
            method,
            parameter_list,
        )
        return res
