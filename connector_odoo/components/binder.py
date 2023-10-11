# © 2013 Guewen Baconnier,Camptocamp SA,Akretion
# © 2016 Sodexis
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

from odoo.addons.component.core import Component
from odoo import tools


class OdooModelBinder(Component):
    """Bind records and give odoo/odoo ids correspondence

    Binding models are models called ``odoo.{normal_model}``,
    like ``odoo.res.partner`` or ``odoo.product.product``.
    They are ``_inherits`` of the normal models and contains
    the Odoo ID, the ID of the Odoo Backend and the additional
    fields belonging to the Odoo instance.
    """

    _name = "odoo.binder"
    _inherit = ["base.binder", "base.odoo.connector"]

    def to_internal(self, external_id, unwrap=False):
        """
        INHERITED to use default_backend_id instead of backend_id

        Give the Odoo recordset for an external ID

        :param external_id: external ID for which we want
                            the Odoo ID
        :param unwrap: if True, returns the normal record
                       else return the binding record
        :return: a recordset, depending on the value of unwrap,
                 or an empty recordset if the external_id is not mapped
        :rtype: recordset
        """
        context = self.env.context
        default_backend_id = self.env.company.default_odoo_backend_id
        bindings = self.model.with_context(active_test=False).search(
            [
                (self._external_field, "=", tools.ustr(external_id)),
                (self._backend_field, "=", default_backend_id.id),
            ]
        )
        if not bindings:
            if unwrap:
                return self.model.browse()[self._odoo_field]
            return self.model.browse()
        bindings.ensure_one()
        if unwrap:
            bindings = bindings[self._odoo_field]
        bindings = bindings.with_context(**context)
        return bindings

    def wrap_binding(self, regular, browse=False):
        """For a normal record, gives the binding record.

        Example: when called with a ``product.product`` id,
        it will return the corresponding ``odoo.product.product`` id.
        it assumes that bind_ids is the name used for bind regular to
        external objects
        :param browse: when True, returns a browse_record instance
                       rather than an ID
        """
        try:
            bindings = regular.bind_ids
        except BaseException as e:
            raise ValueError(
                "Cannot wrap model %s, because it has no %s fields"
                % (self.model._name, "bind_ids")
            ) from e
        bind = bindings.filtered(lambda b: b.backend_id.id == self.backend_record.id)
        bind.ensure_one()
        return bind[self._external_field]
