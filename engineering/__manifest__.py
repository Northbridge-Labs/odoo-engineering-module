# -*- coding: utf-8 -*-
{
    'name': 'Engineering',

    'summary': 'Manage engineering projects: BoM/BoQ, customer quotation, MO and timeline',

    'description': """
Engineering module
==================

Manages the engineering-to-quotation-to-manufacturing flow:

* Engineering team drafts a Bill of Materials (material specs) and a
  Bill of Quantities (service scope) for a customer work order.
* Commercial department applies a markup and produces a customer-facing
  quotation that exposes only the final project estimate price.
* On customer approval, a Manufacturing Order is generated from the
  approved BoM (with BoQ services carried as non-stock work lines) and
  triggers Purchase RFQs for stock shortages.
* The engineering project is linked to the Project module to manage the
  construction timeline.

Follows SOLID principles and Odoo 18 module development best practices.
    """,

    'author': 'Lucas Pereira, Northbridge Labs',
    'maintainer': 'Northbridge Labs',
    'website': 'https://www.northbridgelabs.com.br',
    'support': 'https://github.com/Northbridge-Labs/odoo-engineering-module/issues',

    'category': 'Services/Engineering',

    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'price': 0.00,
    'currency': 'USD',

    'depends': [
        'base',
        'product',
        'uom',
        'sale',
        'stock',
        'mrp',
        'purchase',
        'project',
    ],

    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        'data/sequence_data.xml',
        'data/product_data.xml',
        'views/menus.xml',
        'wizard/request_revision_views.xml',
        'views/engineering_project_views.xml',
        'views/engineering_bom_views.xml',
        'views/engineering_boq_views.xml',
        'views/engineering_quotation_views.xml',
        'views/project_project_views.xml',
        'report/quotation_report.xml',
    ],
    'demo': [
        'demo/demo.xml',
    ],
    'application': True,
    'installable': True,
    'auto_install': False,
}