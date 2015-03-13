# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2011 NovaPoint Group LLC (<http://www.novapointgroup.com>)
#    Copyright (C) 2004-2010 OpenERP SA (<http://www.openerp.com>)
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from openerp.osv import fields, osv
from openerp.tools.translate import _
import xml2dic


class res_partner(osv.osv):
    _inherit = 'res.partner'
    
    def _method_get(self, cr, uid, context=None):
        res = super(res_partner, self)._method_get(cr, uid, context=context)
        res.append(('ups.account', 'UPS'))
        return res
    _columns = {
            'address_validation_method': fields.selection(_method_get, 'Address Validation Method', size=32),
             }

res_partner()

class sale_order(osv.osv):
    _inherit = "sale.order"

    def action_ship_create(self, cr, uid, ids, context=None):
        pick_obj = self.pool.get('stock.picking')
        result = super(sale_order, self).action_ship_create(cr, uid, ids, context=context)
        if result:
            for sale in self.browse(cr, uid, ids):
                if sale.ship_company_code == 'ups':
                    pick_ids = pick_obj.search(cr, uid, [('sale_id', '=', sale.id), ('picking_type_code', '=', 'outgoing')], context=context)
                    if pick_ids:
                        vals = {
                            'ship_company_code': 'ups',
                            'logis_company': sale.logis_company and sale.logis_company.id or False,
                            'shipper': sale.ups_shipper_id and sale.ups_shipper_id.id or False,
                            'ups_service': sale.ups_service_id and sale.ups_service_id.id or False,
                            'ups_pickup_type': sale.ups_pickup_type,
                            'ups_packaging_type': sale.ups_packaging_type and sale.ups_packaging_type.id or False,
                            'ship_from_address':sale.ups_shipper_id and sale.ups_shipper_id.address and sale.ups_shipper_id.address.id or False,
                            'shipcharge':sale.shipcharge or False,
                            'packages_ids': [(0,0, {
                                                    'package_type':sale.ups_packaging_type and sale.ups_packaging_type.id or False,
                                                    
                                                    
                                                    })]
                            }
                        pick_obj.write(cr, uid, pick_ids, vals)
                else:
                    pick_ids = pick_obj.search(cr, uid, [('sale_id', '=', sale.id), ('type', '=', 'out')])
                    if pick_ids:
                        pick_obj.write(cr, uid, pick_ids, {'shipper': False, 'ups_service': False}, context=context)
        return result

    def _get_company_code(self, cr, user, context=None):
        res = super(sale_order, self)._get_company_code(cr, user, context=context)
        res.append(('ups', 'UPS'))
        return res
    
    def onchage_service(self, cr, uid, ids, ups_shipper_id=False, context=None):
         vals = {}
         service_type_ids = []
         if ups_shipper_id:
             shipper_obj = self.pool.get('ups.account.shipping').browse(cr, uid, ups_shipper_id)
             for shipper in shipper_obj.ups_shipping_service_ids:
                 service_type_ids.append(shipper.id)
         domain = [('id', 'in', service_type_ids)]
         return {'domain': {'ups_service_id': domain}}
     
    def onchange_ups_shipper_id(self, cr, uid, ids, ups_shipper_id = False, context=None):

        res = {}
        
        service_type_ids = []
        if ups_shipper_id:
            shipper_obj = self.pool.get('ups.account.shipping').browse(cr, uid, ups_shipper_id)
            for shipper in shipper_obj.ups_shipping_service_ids:
                service_type_ids.append(shipper.id)
        domain = [('id', 'in', service_type_ids)]
        
        if ups_shipper_id:
            partner_id = self.pool.get('ups.account.shipping').browse(cr, uid, ups_shipper_id, context=context).partner_id.id
            res = {'value': {'transport_id' : partner_id},
                   'domain': {'ups_service_id': domain}}
        return res 
    
    def onchange_delivery_method(self, cr, uid, ids, delivery_method, context=None):
        
        res = super(sale_order, self).onchange_delivery_method(cr, uid, ids, delivery_method, context=context)
        
        ups_shipper_ids = []
        ups_shipper_id=False
        if delivery_method:
            deliver_method_obj = self.pool.get('delivery.method').browse(cr, uid, delivery_method, context=context)
            if deliver_method_obj.ship_company_code == 'ups':
                for shipper in deliver_method_obj.ups_shipping_account_ids:
                    ups_shipper_ids.append(shipper.id) 
                if ups_shipper_ids :
                    ups_shipper_id=ups_shipper_ids[0]
            
            res['value']['ship_company_code'] = deliver_method_obj.ship_company_code
            res['value']['sale_account_id'] = deliver_method_obj.ship_account_id.id
            res['value']['ups_shipper_id'] = ups_shipper_id  

        return res
     
    def _method_get(self, cr, uid, context=None):
        res = super(sale_order, self)._method_get(cr, uid, context=context)
        res.append(('ups.account', 'UPS'))
        return res
    
    _columns = {
        'payment_method':fields.selection([
            ('cc_pre_auth', 'Credit Card – PreAuthorized'),
            ('invoice', 'Invoice'),
            ('cod', 'COD'),
            ('p_i_a', 'Pay In Advance'),
            ('pay_pal', 'Paypal'),
            ('no_charge', 'No Charge')], 'Payment Method'),
        'ship_company_code': fields.selection(_get_company_code, 'Logistic Company', method=True, size=64),
        'ups_shipper_id': fields.many2one('ups.account.shipping', 'Shipping Account'),
        'ups_service_id': fields.many2one('ups.shipping.service.type', 'Service Type'),
        'ups_pickup_type': fields.selection([
            ('01', 'Daily Pickup'),
            ('03', 'Customer Counter'),
            ('06', 'One Time Pickup'),
            ('07', 'On Call Air'),
            ('11', 'Suggested Retail Rates'),
            ('19', 'Letter Center'),
            ('20', 'Air Service Center'),
            ], 'Pickup Type'),
        'ups_packaging_type': fields.many2one('shipping.package.type', 'Packaging Type'),
        'shipping_rates': fields.one2many('shipping.rates.sales', 'sales_id', 'Rate Quotes'),
        'status_message': fields.char('Status', size=128, readonly=True),
        # From partner address validation
        'address_validation_method': fields.selection(_method_get, 'Address Validation Method', size=32),
        
    }

    def _get_sale_account(self, cr, uid, context=None):
        if context is None:
            context = {}
        logsitic_obj = self.pool.get('logistic.company')
        user_rec = self.pool.get('res.users').browse(cr , uid, uid, context)
        logis_company = logsitic_obj.search(cr, uid, [])
        if not logis_company:
            return False
        return logsitic_obj.browse(cr, uid, logis_company[0], context).ship_account_id.id

    _defaults = {
        'sale_account_id': _get_sale_account,
        }
    
    def get_rate(self, cr, uid, ids, context=None):
        
        sale_obj = self.pool.get('sale.order')
        
        data = self.browse(cr, uid, ids[0], context=context)
#        sale_obj.write(cr,uid,context.get('active_ids'),{'ups_shipper_id':data.ups_shipper_id.id,
#                                                         'ups_service_id':data.ups_service_id.id,
#                                                         'ups_pickup_type':data.ups_pickup_type,
#                                                         'ups_packaging_type':data.ups_packaging_type.id},context=context)
        if context is None:
            context = {}
#        if not (data['rate_selection'] == 'rate_request' and data['ship_company_code'] == 'ups'):
#            return super(shipping_rate_wizard, self).get_rate(cr, uid, ids, context)
#        if context.get('active_model', False) == 'sale.order':
        weight = data.total_weight_net or 0.00
        
#         invoice = self.pool.get('account.invoice').browse(cr, uid, context['active_id'], context=context)
#         weight = invoice.total_weight_net or 0.00
        receipient_zip = data.partner_id and data.partner_id.zip or ''
        receipient_country_code = data.partner_id.country_id and data.partner_id.country_id.code or ''
        access_license_no = data.ups_shipper_id and  data.ups_shipper_id.accesslicensenumber or ''
        user_id = data.ups_shipper_id and  data.ups_shipper_id.userid or ''
        password = data.ups_shipper_id and data.ups_shipper_id.password or ''
        pickup_type_ups = data.ups_pickup_type
        shipper_zip = data.ups_shipper_id and data.ups_shipper_id.address and data.ups_shipper_id.address.zip or ''
        shipper_country_code =  data.ups_shipper_id and data.ups_shipper_id.address and  data.ups_shipper_id.address.country_id and \
                                data.ups_shipper_id.address.country_id.code or ''
        ups_info_shipper_no = data.ups_shipper_id and data.ups_shipper_id.acc_no or ''
        
        packaging_type_ups = data.ups_packaging_type.code
        test_mode = False
        test_mode = data.delivery_method and data.delivery_method.test_mode
        
        if test_mode:
            url = unicode(data.delivery_method.ship_rate_test_web)
        #                port = data.logis_company.ship_rate_test_port
        else:
            url = unicode(data.delivery_method.ship_rate_web)
#                port = data.logis_company.ship_rate_port
    
#         if data.ups_service_id:
#            request_action ="rate"
#            request_option ="rate"
#            service_type_ups = data.ups_service_id and data.ups_service_id.shipping_service_code or ''            
#         else:
        request_action = "shop"
        request_option = "shop"
        service_type_ups = ''

#            url = 'https://wwwcie.ups.com/ups.app/xml/Rate' or 'https://onlinetools.ups.com/ups.app/xml/Rate'

        rate_request = """<?xml version=\"1.0\"?>
         <AccessRequest xml:lang=\"en-US\">
             <AccessLicenseNumber>%s</AccessLicenseNumber>
             <UserId>%s</UserId>
             <Password>%s</Password>
         </AccessRequest>
         <?xml version=\"1.0\"?>
         <RatingServiceSelectionRequest xml:lang=\"en-US\">
             <Request>
                 <TransactionReference>
                     <CustomerContext>Rating and Service</CustomerContext>
                     <XpciVersion>1.0001</XpciVersion>
                 </TransactionReference>
                 <RequestAction>%s</RequestAction>
                 <RequestOption>%s</RequestOption>
             </Request>
         <PickupType>
             <Code>%s</Code>
         </PickupType>
         <Shipment>
             <Shipper>
                 <Address>
                     <PostalCode>%s</PostalCode>
                     <CountryCode>%s</CountryCode>
                 </Address>
             <ShipperNumber>%s</ShipperNumber>
             </Shipper>
             <ShipTo>
                 <Address>
                     <PostalCode>%s</PostalCode>
                     <CountryCode>%s</CountryCode>
                 <ResidentialAddressIndicator/>
                 </Address>
             </ShipTo>
             <ShipFrom>
                 <Address>
                     <PostalCode>%s</PostalCode>
                     <CountryCode>%s</CountryCode>
                 </Address>
             </ShipFrom>
             <Service>
                 <Code>%s</Code>
             </Service>
             <Package>
                 <PackagingType>
                     <Code>%s</Code>
                 </PackagingType>
                 <PackageWeight>
                     <UnitOfMeasurement>
                         <Code>LBS</Code>
                     </UnitOfMeasurement>
                     <Weight>%s</Weight>
                 </PackageWeight>
             </Package>
         </Shipment>
         </RatingServiceSelectionRequest>""" % (access_license_no, user_id, password,request_action,request_option, pickup_type_ups, shipper_zip,shipper_country_code, 
                                                ups_info_shipper_no,receipient_zip, receipient_country_code, shipper_zip, shipper_country_code, 
                                                service_type_ups, packaging_type_ups, weight)
         
        rates_obj = self.pool.get('shipping.rates.sales')
        so = data.id
        rids = rates_obj.search(cr,uid,[('sales_id','=', so )])
        rates_obj.unlink(cr, uid, rids, context)
        serv_obj = self.pool.get('ups.shipping.service.type')
    
        try:
            print rate_request
            from urllib2 import Request, urlopen, URLError, quote
            request = Request(url.encode('utf-8').strip(), rate_request.encode('utf-8').strip())
            response_text = urlopen(request).read()
        #             p.agent_info = u' '.join((agent_contact, agent_telno)).encode('utf-8').strip()
            print response_text
            
            response_dic = xml2dic.main(response_text)
            str_error = ''
            for response in response_dic['RatingServiceSelectionResponse'][0]['Response']:
                if response.get('Error'):
                    for item in response['Error']:
                        if item.get('ErrorDescription'):
                            str_error = item['ErrorDescription']
                            self.write(cr, uid, [data.id], {'status_message': "Error : " + item['ErrorDescription'] })
            if not str_error:
        #                     print response_dic
        
                amount = None
                ups_service_id = None
        # Get all the return Shipping rates as options                    
                for response in response_dic['RatingServiceSelectionResponse']:
                    
                    
                    if response.get('RatedShipment'):
                        
                        warning = None
                        vals = {}
                        for val in response['RatedShipment']:
                            if val.get('TotalCharges'):
                                vals['totalcharges'] = float(val['TotalCharges'][1]['MonetaryValue'])
                            if val.get('GuaranteedDaysToDelivery'):
                                vals['daystodelivery'] = val['GuaranteedDaysToDelivery']
                            if val.get('Service'):
                                service_code = val['Service'][0]['Code'] 
                                service = serv_obj.search(cr,uid,[('shipping_service_code','=',service_code)])                 
                                vals['service'] =service[0]
                            if val.get('RatedShipmentWarning'):
                                if not warning:
                                    warning =  val['RatedShipmentWarning']
                                else:
                                    warning = warning + ", " + val['RatedShipmentWarning']
                                     
                        # get the lowest cost shipping rate as default on Sales Order                                       
                                     
                        if (amount is None) or amount > vals['totalcharges']: 
                            amount = vals['totalcharges']
                            ups_service_id = vals['service']
                            status_mesage = warning 
                            
                        vals['ratedshipmentwarning'] = warning
                        vals['sales_id'] = so
                        rates_obj.create(cr,uid,vals,context)
                sale_obj.write(cr,uid,so,{'shipcharge':amount or 0.00,'ups_service_id':ups_service_id,'status_message':warning},context=context)
        
                return True
                rates_obj.write(cr, uid, context.get('active_ids'), { 'status_message': 'Success!'},context=context)
        except URLError, e:
            if hasattr(e, 'reason'):
                print 'Could not reach the server, reason: %s' % e.reason
            elif hasattr(e, 'code'):
                print 'Could not fulfill the request, code: %d' % e.code
            raise
           
       
    #         mod, modid = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'shipping_api_ups', 'view_for_shipping_rate_wizard_shipping')
        return True

sale_order()

class shipping_rates_sales(osv.osv):
    
    _name = "shipping.rates.sales"
    _description = "Shipping Rate Estimate Charges"
    _columns = {    
        'totalcharges': fields.float('Total Charges'),
        'ratedshipmentwarning': fields.char('Shipment Warning', size=512),
        'sales_id': fields.many2one('sale.order', 'Sales Order', required=True, ondelete='cascade',),
        'daystodelivery': fields.integer('Days to Delivery'),
        'service': fields.many2one('ups.shipping.service.type', 'Shipping Service' ),
        }
    
    def select_ship_service(self,cr,uid,ids,context=None):
        sale_obj = self.pool.get('sale.order')
        vals = {}
        for service in self.browse(cr, uid, ids, context=context):
            self.pool.get('sale.order')
            vals['ups_service_id']  = service.service.id
            vals['shipcharge'] = service.totalcharges
            vals['ship_service'] = service.service.description
            sale_obj.write(cr,uid,[service.sales_id.id],vals,context)
        mod, modid = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale', 'view_order_form')
        return {
            'name':_("Sale Order"),
            'view_mode': 'form',
            'view_id': modid,
            'view_type': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
        #    'target':'new',
         #   'nodestroy': True,
            'domain': '[]',
            'res_id': service.sales_id.id,
            'context':context,
        }
                      
        return True
    
shipping_rates_sales()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
