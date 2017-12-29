# -*- coding: utf-8 -*-
# Copyright 2017 Florent THOMAS (Mind And Go), Odoo Community Association (OCA)
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

{
    'name': 'Connector Odoo',
    'summary': """
        Base connector for Odoo To Odoo scenarios""",
    'version': '10.0.1.0.0',
    'category': 'Connector',
    'license': 'AGPL-3',
    'author': 'Florent THOMAS (Mind And Go), Odoo Community Association (OCA)',
    "application": False,
    "installable": True,
    "pre_init_hook": "pre_init_hook",
    "post_init_hook": "post_init_hook",
    "post_load": "post_load",
    "uninstall_hook": "uninstall_hook",
    "external_dependencies": {
        "python": [
            'OdooRPC'
            ],
        "bin": [],
    },
    "depends": [
        "base",
        "product",
        "connector",
        "connector_base_product",
    ],
    "data": [
#         "security/some_model_security.xml",
#         "security/ir.model.access.csv",
#         "templates/assets.xml",
        "views/odoo_backend.xml",
#         "views/res_partner_view.xml",
#         "wizards/wizard_model_view.xml",
    ],
    "demo": [
#         "demo/res_partner_demo.xml",
    ],
    "qweb": [
#         "static/src/xml/module_name.xml",
    ]
}
