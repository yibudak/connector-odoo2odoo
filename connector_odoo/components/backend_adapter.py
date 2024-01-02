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
        context=None,
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
        return [
            q["id"]
            for q in odoo_api.search(
                model=ext_model,
                fields=fields or ["id"],
                domain=domain or [],
                offset=offset,
                limit=limit,
                order=order,
                context=context,
                get_passive=self._get_passive,
            )
        ]

    # pylint: disable=W8106,W0622
    def read(self, res_id, model=None, context=None):
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
            model=ext_model,
            res_id=res_id,
            context=context,
            get_passive=self._get_passive,
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
