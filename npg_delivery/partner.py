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

from openerp.osv import fields, osv

class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def _method_get(self, cr, uid, context=None):
        list = [("none", "None")]
        return list
    
    _columns = {
        'property_delivery_carrier': fields.property(
          type='many2one',
          relation='delivery.carrier',
          string="Delivery Method",
          view_load=True,
          help="This delivery method will be used when invoicing from picking."),
        'last_address_validation': fields.date('Last Address Validation', readonly=True),
        'address_validation_method': fields.selection(_method_get, 'Address Validation Method', size=32),
        'classification': fields.selection([('',''),('0','Unknown'),('1','Commercial'),('2','Residential')], 'Classification'), 
         }
    
    '''
    Change the address disply as us format
    '''
    
    def _get_address_validation_method(self, cr, uid, context={}):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        return user and user.company_id and user.company_id.address_validation_method


    def search(self, cr, uid, args, offset=0, limit=None, order=None,
            context=None, count=False):
        if context is None:
            context = {}
        results =[]
        
        if context.get('search_transport_company', False):
            
            cr.execute(
                   ''' SELECT distinct
                      partner_id
                    FROM 
                      public.delivery_carrier 
                    ''')
            results = cr.fetchall()
            
            args += [('id', 'in', results)]

        return super(res_partner, self).search(cr, uid, args, offset, limit,
                order, context=context, count=count)
        
    def name_search(self, cr, uid, name='', args=None, operator='ilike', context=None, limit=100):
        if not args:
            args = []
            
        if context.get('search_transport_company', False):

            positive_operators = ['=', 'ilike', '=ilike', 'like', '=like']
            cr.execute(
                   ''' SELECT distinct
                      partner_id
                    FROM 
                      public.delivery_carrier 
                    ''')
            results = cr.fetchall()
            
            if results:
                args += [('id', 'in', results)]
    
            ids = []
            if operator in positive_operators:
                ids = self.search(cr, uid, [('name',operator,name)]+ args, limit=limit, context=context)
            ids = self.search(cr, uid, args, limit=limit, context=context)
            result = self.name_get(cr, uid, ids, context=context) 
            return result  
        else:
            
            return super(res_partner, self).name_search(cr, uid, name, args, operator,context, limit=limit)

        
        
res_partner()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

