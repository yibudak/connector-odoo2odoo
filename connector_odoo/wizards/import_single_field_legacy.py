# Copyright 2023 Yiğit Budak (https://github.com/yibudak)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl)
from odoo import fields, models, api


class ImportSingleFieldLegacyWizard(models.TransientModel):
    _name = "import.single.field.legacy.wizard"

    def _get_default_backend(self):
        return self.env["odoo.backend"].search([], limit=1).id

    backend_id = fields.Many2one(
        "odoo.backend", required=True, default=_get_default_backend
    )
    model_id = fields.Many2one(
        "ir.model", required=True, domain="[('model', 'like', 'odoo.%')]"
    )
    field_name = fields.Char(required=True)
    to_field_name = fields.Char(required=True)
    force = fields.Boolean(default=True)

    def action_import(self):
        self.ensure_one()
        connection = self.backend_id.get_connection()
        imported_records = self.env[self.model_id.model].search(
            [("backend_id", "=", self.backend_id.id)]
        )
        external_records = connection.search(
            model=self.model_id.model.lstrip("odoo."),
            domain=[
                "|",
                ["active", "=", True],
                ["active", "=", False],
                ["id", "in", imported_records.mapped("external_id")],
            ],
            fields=[self.field_name],
        )
        record_dict = {rec.external_id: rec for rec in imported_records}
        external_records = {rec["id"]: rec for rec in external_records}

        for record_external_id, record in record_dict.items():
            data = external_records.get(record_external_id)
            if data:
                record.write({self.to_field_name: data[self.field_name]})

        return True
