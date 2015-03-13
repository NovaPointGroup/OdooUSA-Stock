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
import openerp.addons.decimal_precision as dp

# Overloaded sale_order to manage carriers :
class sale_order(osv.osv):
    _inherit = 'sale.order'
    
    def _make_invoice(self, cr, uid, order, lines, context=None):
        inv_id = super(sale_order, self)._make_invoice(cr, uid, order, lines, context=None)
        if inv_id:
            if order.sale_account_id:
                inv_obj = self.pool.get('account.invoice')
                inv_obj.write(cr, uid, inv_id, {
                    'shipcharge': order.shipcharge,
                    'ship_service': order.ship_service,
#                    'ship_method_id': order.ship_method_id.id,
                    'sale_account_id': order.sale_account_id.id,
                    })
                inv_obj.button_reset_taxes(cr, uid, [inv_id], context=context)
        return inv_id

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()

    def _amount_shipment_tax(self, cr, uid, shipment_taxes, shipment_charge):
        val = 0.0
        for c in self.pool.get('account.tax').compute_all(cr, uid, shipment_taxes, shipment_charge, 1)['taxes']:
            val += c.get('amount', 0.0)
        return val

    def _amount_all(self, cr, uid, ids, field_name, arg, context=None):
        cur_obj = self.pool.get('res.currency')
        res = super(sale_order, self)._amount_all(cr, uid, ids, field_name, arg, context=context)
        for order in self.browse(cr, uid, ids, context=context):
            cur = order.pricelist_id.currency_id
            tax_ids =[]# order.ship_method_id and order.ship_method_id.shipment_tax_ids
            if tax_ids:
                val = self._amount_shipment_tax(cr, uid, tax_ids, order.shipcharge)
                res[order.id]['amount_tax'] += cur_obj.round(cr, uid, cur, val)
                res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'] + order.shipcharge
            elif order.shipcharge:
                res[order.id]['amount_total'] = res[order.id]['amount_untaxed'] + res[order.id]['amount_tax'] + order.shipcharge
        return res
    
    def _get_company_code(self, cr, user, context=None):
        return [('grid', 'Price Grid')]
    
    def _get_address_validation_method(self, cr, uid, context=None):
        if context is None: context = {}
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user and user.company_id and user.company_id.address_validation_method
    
    def _validated(self, cr, uid, ids, name, args, context=None):
        res = {}
        for sale_order in self.browse(cr,uid,ids,context=context):
            if sale_order.partner_invoice_id.last_address_validation and sale_order.partner_order_id.last_address_validation and sale_order.partner_shipping_id.last_address_validation:
                res[sale_order.id] = True
            else:
                res[sale_order.id] = False
        return res
    
    def _method_get(self, cr, uid, context=None):
        list = [("none", "None")]
        return list

    
    _columns = {
        'carrier_id':fields.many2one("delivery.carrier", "Delivery Service", help="The Delivery service Choices defined for Transport or Logistics Company"),
        'delivery_method': fields.many2one("delivery.method","Delivery Method", help=" The Delivery Method or Category"),
        'transport_id':fields.many2one("res.partner", "Transport Company", help="The partner company responsible for Shipping"),
        'shipcharge': fields.float('Shipping Cost'),
        'ship_service': fields.char('Delivery Service', size=128, readonly=True),
        'ship_company_code': fields.selection(_get_company_code, 'Ship Company', method=True, size=64),
#        'ship_method_id': fields.many2one('shipping.rate.config', 'Shipping Method', readonly=True),
        'sale_account_id': fields.many2one('account.account', 'Cost Account',
                                           help='This account represents the g/l account for booking shipping income.'),
        'amount_untaxed': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Sale Price'), string='Untaxed Amount',
            store = {
               'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line', 'shipcharge'], 10),
               'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
               },
               multi='sums', help="The amount without tax."),
        'amount_tax': fields.function(_amount_all, method=True, digits_compute=dp.get_precision('Sale Price'), string='Taxes',
            store = {
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line',  'shipcharge'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
                },
                multi='sums', help="The tax amount."),
        'amount_total': fields.function(_amount_all, method=True, digits_compute= dp.get_precision('Sale Price'), string='Total',
            store = {
                'sale.order': (lambda self, cr, uid, ids, c={}: ids, ['order_line', 'shipcharge'], 10),
                'sale.order.line': (_get_order, ['price_unit', 'tax_id', 'discount', 'product_uom_qty'], 10),
                },
                 multi='sums', help="The total amount."),
                 
        # From partner address validation module.
      
        'hide_validate':fields.function(_validated, method=True, string='Hide Validate', type='boolean', store=False),
        'address_validation_method': fields.selection(_method_get, 'Address Validation Method', size=32),
      
      }
    
    _defaults = {
        'address_validation_method':_get_address_validation_method,
    }
    
    def create(self, cr, uid, vals, context=None):
        if vals.get('name','/')=='/':
            vals['name'] = self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/'
        if vals.has_key('carrier_id') and vals['carrier_id']:
            carrier_id =vals['carrier_id']
            carrier_obj = self.pool.get('delivery.carrier').browse(cr, uid, carrier_id, context=context)
            vals['transport_id']=carrier_obj.partner_id.id
            vals['ship_service']=carrier_obj.name
        return super(sale_order, self).create(cr, uid, vals, context=context)
    
    def write(self, cr, uid,ids, vals, context=None):
        if vals.has_key('carrier_id') and vals['carrier_id']:
            carrier_id =vals['carrier_id']
            carrier_obj = self.pool.get('delivery.carrier').browse(cr, uid, carrier_id, context=context)
            vals['transport_id']=carrier_obj.partner_id.id
            vals['ship_service']=carrier_obj.name
        return super(sale_order, self).write(cr, uid,ids, vals, context=context)


    def onchange_partner_id(self, cr, uid, ids, part, context=None):
        result = super(sale_order, self).onchange_partner_id(cr, uid, ids, part, context=context)
        if part:
            dtype = self.pool.get('res.partner').browse(cr, uid, part, context=context).property_delivery_carrier.id
            result['value']['carrier_id'] = dtype
        return result
    
    def onchange_carrier_id(self, cr, uid, ids, carrier, context=None):

       
        res = {}
        if carrier:
            carrier_obj = self.pool.get('delivery.carrier').browse(cr, uid, carrier, context=context)
            res = {'value': {'transport_id' : carrier_obj.partner_id.id,
                            'ship_service' : carrier_obj.name }}
        return res
    
    def onchange_delivery_method(self, cr, uid, ids, delivery_method, context=None):
        
        res = {'value': {'carrier_id':False,
                         'transport_id':False,
                         'ship_service':False,},
               }
        return res
            
#     def _prepare_order_picking(self, cr, uid, order, context=None):
#         result = super(sale_order, self)._prepare_order_picking(cr, uid, order, context=context)
#         result.update(carrier_id=order.carrier_id.id)
#         return result
    
    def action_ship_create(self, cr, uid, ids, context=None):
        pick_obj = self.pool.get("stock.picking")
        ret = super(sale_order, self).action_ship_create(cr, uid, ids, context=context)
        for sale_obj in self.browse(cr, uid, ids, context=context):
            pick_obj.write(cr, uid, [x.id for x in sale_obj.picking_ids], {'carrier_id': sale_obj.carrier_id.id}, context=context)
                    
        return ret
    
    def delivery_set(self, cr, uid, ids, context=None):
        order_obj = self.pool.get('sale.order')
        line_obj = self.pool.get('sale.order.line')
        grid_obj = self.pool.get('delivery.grid')
        carrier_obj = self.pool.get('delivery.carrier')
        acc_fp_obj = self.pool.get('account.fiscal.position')
        for order in self.browse(cr, uid, ids, context=context):
            grid_id = carrier_obj.grid_get(cr, uid, [order.carrier_id.id], order.partner_shipping_id.id)
            if not grid_id:
                raise osv.except_osv(_('No Grid Available!'), _('No grid matching for this carrier!'))

            if not order.state in ('draft', 'sent'):
                raise osv.except_osv(_('Order not in Draft State!'), _('The order state have to be draft to add delivery lines.'))

            grid = grid_obj.browse(cr, uid, grid_id, context=context)
            price_unit= grid_obj.get_price_sale(cr, uid, grid.id, order, time.strftime('%Y-%m-%d'), context)
            order_obj.write(cr,uid,ids,{'ship_service':order.carrier_id.name,'shipcharge':price_unit})
#            taxes = grid.carrier_id.product_id.taxes_id
#            fpos = order.fiscal_position or False
#            taxes_ids = acc_fp_obj.map_tax(cr, uid, fpos, taxes)
#            #create the sale order line
#            line_obj.create(cr, uid, {
#                'order_id': order.id,
#                'name': grid.carrier_id.name,
#                'product_uom_qty': 1,
#                'product_uom': grid.carrier_id.product_id.uom_id.id,
#                'product_id': grid.carrier_id.product_id.id,
#                'price_unit': grid_obj.get_price_sale(cr, uid, grid.id, order, time.strftime('%Y-%m-%d'), context),
#                'tax_id': [(6,0,taxes_ids)],
#                'type': 'make_to_stock'
#            })
             
        return True
    
    def action_invoice_create(self, cr, uid, ids, context=None):
        inv_id = super(sale_order, self).action_invoice_create(cr, uid, ids, context)
        for so in self.browse(cr,uid,ids,context):
            vars = {'transport_id':so.transport_id.id or False,
                  'carrier_id':so.carrier_id.id or False,
                  'delivery_method':so.delivery_method.id or False
                  }
                
            self.pool.get('account.invoice').write(cr,uid,inv_id,vars)
        return inv_id
        #return {'type': 'ir.actions.act_window_close'} action reload?

sale_order()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

