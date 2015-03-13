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

import time
from openerp.osv import fields,osv
from openerp.tools.translate import _



# Overloaded sale_order to manage carriers :
class purchase_order(osv.osv):
    _inherit = 'purchase.order'
    _columns = {
        'carrier_id':fields.many2one("delivery.carrier", "Delivery Service", help="The Delivery service Choices defined for Transport or Logistics Company"),
        'delivery_method': fields.many2one("delivery.method","Delivery Method", help=" The Delivery Method or Category"),
        'transport_id':fields.many2one("res.partner", "Transport Company", help="The partner company responsible for Shipping"),
        'warehouse_id': fields.many2one('stock.warehouse', 'Destination Warehouse'), 
    }

    
    def delivery_set(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('purchase.order')
        line_obj = self.pool.get('purchase.order.line')
        grid_obj = self.pool.get('delivery.grid')
        carrier_obj = self.pool.get('delivery.carrier')
        acc_fp_obj = self.pool.get('account.fiscal.position')
        for order in self.browse(cr, uid, ids, context=context):
            
            destination=order.dest_address_id.id or False
            if not destination:
                destination = order.warehouse_id.partner_id.id or False
            
            grid_id = carrier_obj.grid_get(cr, uid, [order.carrier_id.id], destination )
            if not grid_id:
                raise osv.except_osv(_('No Grid Available!'), _('No grid matching for this carrier!'))

            if not order.state in ('draft', 'sent'):
                raise osv.except_osv(_('Order not in Draft State!'), _('The order state have to be draft to add delivery lines.'))

            grid = grid_obj.browse(cr, uid, grid_id, context=context)

            #taxes = grid.carrier_id.product_id.taxes_id
            #fpos = order.fiscal_position or False
            #taxes_ids = acc_fp_obj.map_tax(cr, uid, fpos, taxes)
            #create the purchase order line
              
            vals = {
                'order_id': order.id,
                'name': grid.carrier_id.name,
                'product_qty': 1,
#                 'product_uom': grid.carrier_id.product_id.uom_id.id,
#                 'product_id': grid.carrier_id.product_id.id,
                'price_unit': grid_obj.get_price_purchase(cr, uid, grid.id, order, time.strftime('%Y-%m-%d'), context),
#                 'tax_id': [(6,0,taxes_ids)],
                'date_planned':order.date_order,
                }
            
            line_obj.create(cr, uid, vals)
        return True
  
    def action_invoice_create(self, cr, uid, ids, context=None):
        inv_id = super(purchase_order, self).action_invoice_create(cr, uid, ids, context)
        for po in self.browse(cr,uid,ids,context):
            vars = {'transport_id':po.transport_id.id or False,
                  'carrier_id':po.carrier_id.id or False,
                  'delivery_method':po.delivery_method.id or False,
                  }
                
            self.pool.get('account.invoice').write(cr,uid,inv_id,vars)
        return inv_id
  
purchase_order()


# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

