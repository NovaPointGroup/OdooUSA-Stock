# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2004-2010 Tiny SPRL (<http://tiny.be>).
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################


{
    'name': 'NPG Delivery Costs',
    'version': '1.0',
    'category': 'Sales Management',
    'description': """
Allows you to add delivery methods in sale orders and picking.
==============================================================

You can define your own carrier and delivery grid for prices. When creating 
invoices from picking, OpenERP is able to add and compute the shipping line.
""",
    'author': 'Novapoint Group, Inc, OpenERP SA',
    'depends': ['sale','sale_weight', 'purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/response_data_view.xml',
        'wizard/address_validate_view.xml',
        'wizard/saleorder_validation_view.xml',
        'delivery_report.xml',
        'views/delivery_view.xml',
        'views/res_company_view.xml',
        'views/partner_view.xml',
        'views/stock_picking_view.xml',
        'views/sales_order_view.xml',
        'views/purchase_order_view.xml',
        'views/account_invoice_view.xml',
        'delivery_data.xml',
        'views/delivery_menus.xml',
    ],
    'demo': ['delivery_demo.xml'],
    'test': ['test/delivery_cost.yml',
             'test/delivery_chained_pickings.yml',
            ],
    'installable': True,
    'auto_install': False,
    'images': ['images/1_delivery_method.jpeg','images/2_delivery_pricelist.jpeg'],
}
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
