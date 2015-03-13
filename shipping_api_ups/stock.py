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

from xml.dom.minidom import Document
import httplib
import base64
import time
import datetime
from urlparse import urlparse
from PIL import Image
import tempfile
from mako.template import Template
import logging
from openerp import tools
from openerp.tools.translate import _
from openerp.osv import fields, osv
import os
# from lxml import etree

# from StringIO import StringIO
import xml2dic

class shipping_move(osv.osv):
    
    _inherit = "shipping.move"
    _columns = {
        'shipment_identific_no': fields.char('ShipmentIdentificationNumber', size=64,),
        'logo': fields.binary('Logo'),
        'tracking_url': fields.char('Tracking URL', size=512,),
        'service': fields.many2one('ups.shipping.service.type', 'Shipping Service'),
        'shipper': fields.many2one('ups.account.shipping', 'Shipper', help='The specific user ID and shipper. Setup in the company configuration.'),
        }
    
    def print_label(self, cr, uid, ids, context=None):
        if not ids: return []

        return {
            'type': 'ir.actions.report.xml',
            'report_name': 'ship.log.label.print',
            'datas': {
                'model':'shipping.move',
                'id': ids and ids[0] or False,
                'ids': ids and ids or [],
                'report_type': 'pdf'
                },
            'nodestroy': True
        }

    def getTrackingUrl(self, cr, uid, ids, context=None):
        ship_log_obj = self.browse(cr, uid, ids[0], context=context)
        if ship_log_obj.tracking_no:
            tracking_url = "http://wwwapps.ups.com/WebTracking/processInputRequest?sort_by=status&tracknums_displayed=1&\
                            TypeOfInquiryNumber=T&loc=en_US&InquiryNumber1=%s&track.x=0&track.y=0" % ship_log_obj.tracking_no

shipping_move()

class ups_commodity_code(osv.osv):
    _name = 'ups.commodity.code'
    
    _columns = {
                'name':fields.char("Code",size=32),
                'desc':fields.text("Description")
                }
    
ups_commodity_code()

class stock_picking(osv.osv):
    _inherit = "stock.picking"

    def _get_company_code(self, cr, user, context=None):
        res = super(stock_picking, self)._get_company_code(cr, user, context=context)
        res.append(('ups', 'UPS'))
        return res
    
    def _get_ship_type(self, cr, uid, ids, fields, args, context=None):
        """This functional fields compute if the shipping is domestic or international
        """
        register_pool = self.pool.get('event.registration')
        res = {}
        for do in self.browse(cr, uid, ids, context=context):
            res[do.id] = False
            if do.partner_id and do.partner_id.country_id and do.partner_id.country_id.code and not (do.partner_id.country_id.code == 'US' or do.partner_id.country_id.code == 'USA' or do.partner_id.country_id.code == 'CA' or do.partner_id.country_id.code == 'PR'):
                res[do.id] = True
        return res
    
#     def _get_ship_type(self, cr, uid, ids, fields, args, context=None):
#         return self.pool.get('stock.picking')._get_ship_type(cr, uid, ids, fields, args, context)


    
    _columns = {
        'ups_service': fields.many2one('ups.shipping.service.type', 'Service', help='The specific shipping service offered'),
        'shipper': fields.many2one('ups.account.shipping', 'Shipper', help='The specific user ID and shipper. Setup in the company configuration.'),
        'shipment_digest': fields.text('ShipmentDigest'),
        'negotiated_rates': fields.float('NegotiatedRates'),
        'shipment_identific_no': fields.char('ShipmentIdentificationNumber', size=64,),
        'tracking_no': fields.char('TrackingNumber', size=64,),
        'trade_mark': fields.related('shipper', 'trademark', type='char', size=1024, string='Trademark'),
        'ship_company_code': fields.selection(_get_company_code, 'Ship Company', method=True, size=64),
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
        'ups_use_cc': fields.boolean('Credit Card Payment'),
        'ups_cc_type': fields.selection([
            ('01', 'American Express'),
            ('03', 'Discover'),
            ('04', 'MasterCard'),
            ('05', 'Optima'),
            ('06', 'VISA'),
            ('07', 'Bravo'),
            ('08', 'Diners Club')
            ], 'Card Type'),
        'ups_cc_number': fields.char('Credit Card Number', size=32),
        'ups_cc_expiaration_date': fields.char('Expiaration Date', size=6, help="Format is 'MMYYYY'"),
        'ups_cc_security_code': fields.char('Security Code', size=4,),
        'ups_cc_address_id': fields.many2one('res.partner', 'Address'),
        'ups_third_party_account': fields.char('Third Party Account Number', size=32),
        'ups_third_party_address_id': fields.many2one('res.partner', 'Third Party Address'),
        'ups_third_party_type': fields.selection([('shipper', 'Shipper'), ('consignee', 'Consignee')], 'Third Party Type'),
        'ups_bill_receiver_account': fields.char('Receiver Account', size=32, help="The UPS account number of Freight Collect"),
        'ups_bill_receiver_address_id': fields.many2one('res.partner', 'Receiver Address'),
        'label_format_id': fields.many2one('shipping.label.type', 'Label Format Code'),
        'comm_code':fields.many2one('ups.commodity.code','Commodity Code'),
        'is_intnl':fields.function(_get_ship_type,type="boolean",string="Is international Shipping"),
        'status_message': fields.char('Status', size=128, readonly=True),
        }

    def onchange_bill_shipping(self, cr, uid, ids, bill_shipping, ups_use_cc, ups_cc_address_id, ups_bill_receiver_address_id, partner_id,
                               shipper, context=None):
        vals = {}
        if bill_shipping == 'shipper':
            if not ups_cc_address_id and shipper:
                ship_address = self.pool.get('ups.account.shipping').read(cr, uid, shipper, ['address'], context=context)['address']
                if ship_address:
                    vals['ups_cc_address_id'] = ship_address[0]
        else:
            vals['ups_use_cc'] = False
        if not ups_bill_receiver_address_id:
            vals['ups_bill_receiver_address_id'] = partner_id
        return {'value' : vals}
    
    def onchange_delivery_method(self, cr, uid, ids, delivery_method, context=None):
        
        res = super(stock_picking, self).onchange_delivery_method(cr, uid, ids, delivery_method, context=context)
        
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
            res['value']['shipper'] = ups_shipper_id  

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
    
    
    

#     def action_process(self, cr, uid, ids, context=None):
#         sale_order_line = []
#         deliv_order = self.browse(cr, uid, ids, context=context)
#         if isinstance(deliv_order, list):
#             deliv_order = deliv_order[0]
#         do_transaction = True
#         sale = deliv_order.sale_id
#         if sale and sale.payment_method == 'cc_pre_auth' and not sale.invoiced:
#             rel_voucher = sale.rel_account_voucher_id
#             rel_voucher_id = rel_voucher and rel_voucher.id or False
#             if rel_voucher_id and rel_voucher.state != 'posted' and rel_voucher.cc_auth_code:
#                 do_transaction = False
#                 vals_vouch = {'cc_p_authorize': False, 'cc_charge': True}
#                 if 'trans_type' in rel_voucher._columns.keys():
#                     vals_vouch.update({'trans_type': 'AuthCapture'})
#                 self.pool.get('account.voucher').write(cr, uid, [rel_voucher_id], vals_vouch, context=context)
#                 do_transaction = self.pool.get('account.voucher').authorize(cr, uid, [rel_voucher_id], context=context)
#         if not do_transaction:
#             self.write(cr, uid, ids, {'ship_state': 'hold', 'ship_message': 'Unable to process creditcard payment.'})
#             cr.commit()
#             raise osv.except_osv(_('Final credit card charge cannot be completed!'), _("Please hold shipment and contact customer service.."))
#         return super(stock_picking_out, self).action_process(cr, uid, ids, context=context)
   


    def action_done(self, cr, uid, ids, context=None):
        res = super(stock_picking, self).action_done(cr, uid, ids, context=context)

        for picking in self.browse(cr, uid, ids, context=context):
            vals = {}
            service_type_obj = self.pool.get('ups.shipping.service.type')
            ship_service = picking.sale_id and picking.sale_id.ship_service
            if ship_service:
                service_type_ids = service_type_obj.search(cr, uid, [('description', 'like', ship_service)], context=context)
                if service_type_ids:
                  vals['ups_service'] = service_type_ids[0]
                  service_type = service_type_obj.browse(cr, uid, service_type_ids[0], context=context)
                  if service_type.ups_account_id:
                    vals['shipper'] = service_type.ups_account_id.id
                    if service_type.ups_account_id.logistic_company_id:
                        vals['logis_company'] = service_type_obj.ups_account_id.logistic_company_id.id
        return True
    
    def on_change_sale_id(self, cr, uid, ids, sale_id=False, state=False, context=None):
        vals = {}
        if sale_id:
            sale_obj = self.pool.get('sale.order').browse(cr, uid, sale_id)
            service_type_obj = self.pool.get('ups.shipping.service.type')
            ups_shipping_service_ids = service_type_obj.search(cr, uid, [('description', '=', sale_obj.ship_service)], context=context)
            if ups_shipping_service_ids:
                vals['ups_service'] = ups_shipping_service_ids[0]
                shipping_obj = self.pool.get('ups.account.shipping')
                ups_shipping_ids = shipping_obj.search(cr, uid, [('ups_shipping_service_ids', 'in', ups_shipping_service_ids[0])], context=context)
                if ups_shipping_ids:
                    vals['shipper'] = ups_shipping_ids[0]
                    log_company_obj = self.pool.get('logistic.company')
                    logistic_company_ids = log_company_obj.search(cr, uid, [('ups_shipping_account_ids', 'in', ups_shipping_ids[0])], context=context)
                    if logistic_company_ids:
                        vals['logis_company'] = logistic_company_ids[0]
        return {'value': vals}

    def process_void(self, cr, uid, ids, context=None):
        picking_obj = self.pool.get('stock.picking')
        if isinstance(ids, list):
            ids = ids[0]
        do = picking_obj.browse(cr, uid, ids)
        if do.ship_company_code != 'ups':
            return super(stock_picking, self).process_void(cr, uid, ids, context=context)
        data_for_Access_Request = {
            'AccessLicenseNumber': do.shipper.id and do.shipper.accesslicensenumber or '',
            'UserId': do.shipper.id and do.shipper.userid or '',
            'Password': do.shipper.id and do.shipper.password or ''
            }
        response = ''
        if do:
            data_for_void_shipment = {
                'VoidShipmentRequest': {
                    'Request': {
                        'RequestAction': "1",
                        'TransactionReference': {'CustomerContext': ""},
                        },
                    'ShipmentIdentificationNumber': do.logis_company.test_mode and '1Z12345E0193081456' or do.shipment_identific_no or '',
                    'ExpandedVoidShipment': {
                        'ShipmentIdentificationNumber': do.logis_company.test_mode and  '1ZISDE016691676846' or do.shipment_identific_no or '',
                        'TrackingNumber': ''
                        }
                    }
                }

            doc2 = Document()
            VoidShipmentRequest = doc2.createElement("VoidShipmentRequest")
            doc2.appendChild(VoidShipmentRequest)

            Request = doc2.createElement("Request")
            VoidShipmentRequest.appendChild(Request)

            RequestAction = doc2.createElement("RequestAction")
            ptext = doc2.createTextNode(data_for_void_shipment["VoidShipmentRequest"]['Request']['RequestAction'])
            RequestAction.appendChild(ptext)
            Request.appendChild(RequestAction)

            TransactionReference = doc2.createElement("TransactionReference")
            Request.appendChild(TransactionReference)

            CustomerContext = doc2.createElement("CustomerContext")
            ptext = doc2.createTextNode(data_for_void_shipment["VoidShipmentRequest"]['Request']['TransactionReference']['CustomerContext'])
            CustomerContext.appendChild(ptext)
            TransactionReference.appendChild(CustomerContext)

            ExpandedVoidShipment = doc2.createElement("ExpandedVoidShipment")
            VoidShipmentRequest.appendChild(ExpandedVoidShipment)

            ShipmentIdentificationNumber = doc2.createElement("ShipmentIdentificationNumber")
            ptext = doc2.createTextNode(data_for_void_shipment["VoidShipmentRequest"]['ExpandedVoidShipment']['ShipmentIdentificationNumber'])
            ShipmentIdentificationNumber.appendChild(ptext)
            ExpandedVoidShipment.appendChild(ShipmentIdentificationNumber)

            TrackingNumber = doc2.createElement("TrackingNumber")
            ptext = doc2.createTextNode(data_for_void_shipment["VoidShipmentRequest"]['ExpandedVoidShipment']['TrackingNumber'])
            TrackingNumber.appendChild(ptext)

            Request_string2 = doc2.toprettyxml()

            doc1 = Document()
            AccessRequest = doc1.createElement("AccessRequest")
            AccessRequest.setAttribute("xml:lang", "en-US")
            doc1.appendChild(AccessRequest)

            AccessLicenseNumber = doc1.createElement("AccessLicenseNumber")
            ptext = doc1.createTextNode(data_for_Access_Request["AccessLicenseNumber"])
            AccessLicenseNumber.appendChild(ptext)
            AccessRequest.appendChild(AccessLicenseNumber)

            UserId = doc1.createElement("UserId")
            ptext = doc1.createTextNode(data_for_Access_Request["UserId"])
            UserId.appendChild(ptext)
            AccessRequest.appendChild(UserId)

            Password = doc1.createElement("Password")
            ptext = doc1.createTextNode(data_for_Access_Request["Password"])
            Password.appendChild(ptext)
            AccessRequest.appendChild(Password)

            Request_string1 = doc1.toprettyxml()
            Request_string = Request_string1 + Request_string2

            if do.logis_company.test_mode:
                void_web = do.logis_company.ship_void_test_web or ''
                void_port = do.logis_company.ship_void_test_port
            else:
                void_web = do.logis_company.ship_void_web or ''
                void_port = do.logis_company.ship_void_port
            if void_web:
                parse_url = urlparse(void_web)
                serv = parse_url.netloc
                serv_path = parse_url.path
            else:
                raise osv.except_osv(_('Unable to find Shipping URL!'), _("Please configure the shipping company with websites."))
            conn = httplib.HTTPSConnection(serv, void_port)
            res = conn.request("POST", serv_path, Request_string)
            res = conn.getresponse()
            result = res.read()
            response_dic = xml2dic.main(result)
            status = 0
            status_description = ''
            error_description = ''
            for elm in response_dic['VoidShipmentResponse']:
                if 'Response' in elm:
                    for item in elm['Response']:
                        if 'ResponseStatusCode' in item:
                            if item['ResponseStatusCode'] == '1':
                                status = 1
                                clear_vals = {
                                    'ship_message': '',
                                    'negotiated_rates' : 0.00,
                                    'shipment_identific_no' :'',
                                    'tracking_no': '',
                                    'tracking_url': '',
                                    'logo': '',
                                    }
                                self.pool.get('stock.packages').write(cr, uid, [package.id for package in do.packages_ids], clear_vals, context=context)
                                picking_obj.write(cr, uid, do.id,
                                    {'ship_state': 'draft', 'ship_message': 'Shipment has been cancelled.'}, context=context)
                                break
                        if 'ResponseStatusDescription' in item:
                            status_description = item['ResponseStatusDescription']
                            continue
                        if 'Error' in item:
                            for i in item['Error']:
                                if 'ErrorDescription' in i:
                                    error_description = i['ErrorDescription']
                                    picking_obj.write(cr, uid, do.id, {'ship_message': status_description + ': ' + error_description }, context=context)
                                    break
            return status
        return False

    def fill_addr(self, addr_id):
        ret = {
            'AddressLine1': addr_id and addr_id.street or '',
            'AddressLine2': addr_id and addr_id.street2 or '',
            'AddressLine3': "",
            'City': addr_id and addr_id.city or '',
            'StateProvinceCode': addr_id and addr_id.state_id.id and addr_id.state_id.code or '',
            'PostalCode': addr_id and addr_id.zip or '',
            'CountryCode': addr_id and addr_id.country_id.id and addr_id.country_id.code or '',
            'PostalCode': addr_id.zip or ''
        }
        if addr_id and addr_id.classification == '2':
            ret.update({'ResidentialAddress': ""})
        return ret

    def create_ship_accept_request_new(self, cr, uid, do, context=None):
        if not do.shipper:
            return ''
 
        xml_ship_accept_request = """<?xml version="1.0"?>
            <AccessRequest xml:lang='en-US'>
                <AccessLicenseNumber>%(access_l_no)s</AccessLicenseNumber>
                <UserId>%(user_id)s</UserId>
                <Password>%(password)s</Password>
            </AccessRequest>
            """ % {
                'access_l_no': do.shipper.accesslicensenumber or '',
                'user_id': do.shipper.userid or '',
                'password': do.shipper.password,
            }
 
        xml_ship_accept_request += """<?xml version="1.0"?>
            <ShipmentAcceptRequest>
                <Request>
                    <TransactionReference>
                        <CustomerContext>%(customer_context)s</CustomerContext>
                        <XpciVersion>1.0001</XpciVersion>
                    </TransactionReference>
                    <RequestAction>ShipAccept</RequestAction>
                </Request>
                <ShipmentDigest>%(shipment_digest)s</ShipmentDigest>
            </ShipmentAcceptRequest>
            """ % {
                'customer_context': do.name or '',
                'shipment_digest': do.shipment_digest,
            }
             
        return xml_ship_accept_request
# 
    def process_ship_accept(self, cr, uid, do, packages, context=None):
        shipment_accept_request_xml = self.create_ship_accept_request_new(cr, uid, do, context=context)
        if do.logis_company.test_mode:
            acce_web = do.logis_company.ship_accpt_test_web or ''
            acce_port = do.logis_company.ship_accpt_test_port
        else:
            acce_web = do.logis_company.ship_accpt_web or ''
            acce_port = do.logis_company.ship_accpt_port
        if acce_web:
            parse_url = urlparse(acce_web)
            serv = parse_url.netloc
            serv_path = parse_url.path
        else:
            raise osv.except_osv(_('Unable to find Shipping URL!'), _("Please configure the shipping company with websites."))
 
        conn = httplib.HTTPSConnection(serv, acce_port)
        res = conn.request("POST", serv_path, shipment_accept_request_xml)
        import xml2dic
        res = conn.getresponse()
        result = res.read()
 
        response_dic = xml2dic.main(result)
        NegotiatedRates = ''
        ShipmentIdentificationNumber = ''
        TrackingNumber = ''
        label_image = ''
        control_log_image = ''
        status = 0
         
        status_description = ''
        for response in response_dic['ShipmentAcceptResponse']:
            if response.get('Response'):
                for resp_items in response['Response']:
                    if resp_items.get('ResponseStatusCode') and resp_items['ResponseStatusCode'] == '1':
                        status = 1
                    if resp_items.get('ResponseStatusDescription'):
                        status_description = resp_items['ResponseStatusDescription']
                    if resp_items.get('Error'):
                        for err in resp_items['Error']:
                            if err.get('ErrorSeverity'):
                                status_description += '\n' + err.get('ErrorSeverity')
                            if err.get('ErrorDescription'):
                                status_description += '\n' + err.get('ErrorDescription')
            do.write({'ship_message': status_description})
            
        packages_ids = [package.id for package in do.packages_ids]
         
        if status:
            shipment_identific_number, tracking_number_notes, ship_charge = '', '', 0.0
            for shipmentresult in response_dic['ShipmentAcceptResponse']:
                if shipmentresult.get('ShipmentResults'):
                    package_obj = self.pool.get('stock.packages')
                    for package in response['ShipmentResults']:
                        if package.get('ShipmentIdentificationNumber'):
                            shipment_identific_number = package['ShipmentIdentificationNumber']
                            continue
                        ship_charge += package.get('ShipmentCharges') and float(package['ShipmentCharges'][2]['TotalCharges'][1]['MonetaryValue']) or 0.0
                        if package.get('PackageResults'):
                            label_image = ''
                            tracking_number = ''
                            label_code = ''
                            tracking_url = do.logis_company.ship_tracking_url or ''
                            for tracks in package['PackageResults']:
                                if tracks.get('TrackingNumber'):
                                    tracking_number = tracks['TrackingNumber']
                                    if tracking_url:
                                        try:
                                            tracking_url = tracking_url % tracking_number
                                        except Exception, e:
                                            tracking_url = "Invalid tracking url on shipping company"
                                if tracks.get('LabelImage'):
                                    for label in tracks['LabelImage']:
                                        if label.get('LabelImageFormat'):
                                            for format in label['LabelImageFormat']:
                                                label_code = format.get('Code')
                                        if label.get('GraphicImage'):
                                            label_image = label['GraphicImage']
                                            im_in_raw = base64.decodestring(label_image)
                                            path = tempfile.mktemp('.txt')
                                            temp = file(path, 'wb')
                                            temp.write(im_in_raw)
                                            result = base64.b64encode(im_in_raw)
                                            (dirName, fileName) = os.path.split(path)
                                            self.pool.get('ir.attachment').create(cr, uid,
                                                      {
                                                       'name': fileName,
                                                       'datas': result,
                                                       'datas_fname': fileName,
                                                       'res_model': self._name,
                                                       'res_id': do.id,
                                                       'type': 'binary'
                                                      },
                                                      context=context)
                                            temp.close()
                                            try:
                                                new_im = Image.open(path)
                                                new_im = new_im.rotate(270)
                                                new_im.save(path, 'JPEG')
                                            except Exception, e:
                                                pass
                                            label_from_file = open(path, 'rb')
                                            label_image = base64.encodestring(label_from_file.read())
                                            label_from_file.close()
                                            if label_code == 'GIF':
                                                package_obj.write(cr, uid, packages_ids[packages], {
                                                    'tracking_no': tracking_number,
                                                    'shipment_identific_no': shipment_identific_number,
                                                    'logo': label_image,
                                                    'ship_state': 'in_process',
                                                    'tracking_url': tracking_url,
                                                    'att_file_name': fileName
                                                    
                                                    }, context=context)
                                            else:
                                                package_obj.write(cr, uid, packages_ids[packages], {
                                                    'tracking_no': tracking_number,
                                                    'shipment_identific_no': shipment_identific_number,
                                                    'ship_state': 'in_process',
                                                    'tracking_url': tracking_url,
                                                    'att_file_name': fileName
                                                    }, context=context)
                                                 
                                            if int(time.strftime("%w")) in range(1, 6) or (time.strftime("%w") == '6' and do.sat_delivery):
                                                next_pic_date = time.strftime("%Y-%m-%d")
                                            else:
                                                timedelta = datetime.timedelta(7 - int(time.strftime("%w")))
                                                next_pic_date = (datetime.datetime.today() + timedelta).strftime("%Y-%m-%d")
                                             
                                            package_data = package_obj.read(cr, uid, packages_ids[packages], ['weight', 'description'], context=context)
#                                             i += 1
                                            ship_move_obj = self.pool.get('shipping.move')
                                            if label_code == 'GIF':
                                                ship_move_obj.create(cr, uid, {
                                                    'pick_id': do.id,
                                                    'package_weight': package_data['weight'],
                                                    'partner_id': do.partner_id.id,
                                                    'service': do.ups_service.id,
                                                    'ship_to': do.partner_id.id,
                                                    'ship_from': do.ship_from and do.ship_from_address.id  or \
                                                                 do.shipper and do.shipper.address and do.shipper.address.id,
                                                    'tracking_no': tracking_number,
                                                    'shipment_identific_no': shipment_identific_number,
                                                    'logo': label_image,
                                                    'state': 'ready_pick',
                                                    'tracking_url': tracking_url,
                                                    'package': package_data['description'] and str(package_data['description'])[:126],
                                                    'pic_date': next_pic_date,
                                                    'sale_id': do.sale_id.id and do.sale_id.id or False,
                                                    }, context=context)
                                            else:
                                                ship_move_obj.create(cr, uid, {
                                                    'pick_id': do.id,
                                                    'package_weight': package_data['weight'],
                                                    'partner_id': do.partner_id.id,
                                                    'service': do.ups_service.id,
                                                    'ship_to': do.partner_id.id,
                                                    'ship_from': do.ship_from and do.ship_from_address.id  or \
                                                                 do.shipper and do.shipper.address and do.shipper.address.id,
                                                    'tracking_no': tracking_number,
                                                    'shipment_identific_no': shipment_identific_number,
                                                    'state': 'ready_pick',
                                                    'tracking_url': tracking_url,
                                                    'package': package_data['description'] and str(package_data['description'])[:126],
                                                    'pic_date': next_pic_date,
                                                    'sale_id': do.sale_id.id and do.sale_id.id or False,
                                                    }, context=context)
                                            tracking_number_notes += '\n' + tracking_number
                                            
                        if package.get('ControlLogReceipt'):
                            for items in package['ControlLogReceipt']:
                                if items.get('GraphicImage'):
                                    control_log_image = items['GraphicImage']
                                    im_in_raw = base64.decodestring(control_log_image)
                                    file_name = tempfile.mktemp()
                                    path = file_name + '.html'
                                    temp = file(path, 'wb')
                                    temp.write(im_in_raw)
                                    temp.close()
                                    label_from_file = open(path, 'rb')
                                    control_log_image = base64.encodestring(label_from_file.read())
                                    label_from_file.close()
                                    package_obj.write(cr, uid, packages_ids, {'control_log_receipt': control_log_image, }, context=context)
            do.write({'ship_state': 'ready_pick', 'shipcharge': ship_charge, 'internal_note': tracking_number_notes}, context=context)
        return status, label_code

    def add_product(self, cr, uid, package_obj):
        prods = []
        tot_weight = 0
        for pkg in package_obj.pick_id.packages_ids:
            tot_weight += pkg.weight
        for move_lines in package_obj.pick_id.move_lines:
            product_id = move_lines.product_id
            if move_lines.product_id.supply_method == 'produce':
                produce = "Yes"
            else:
                produce = "NO[1]"
            product = {
                'Description': move_lines.product_id.description or " ",
                'Unit': {
                    'Number': str(int(move_lines.product_qty) or 0),
                    'Value': str((move_lines.product_id.list_price * move_lines.product_qty) or 0),
                    'UnitOfMeasurement': {'Code': "LBS", 'Description': "Pounds"}
                    },
                'CommodityCode': package_obj.pick_id.comm_code and package_obj.pick_id.comm_code.name or "",
                'PartNumber': "",
                'OriginCountryCode': package_obj.pick_id.address_id and package_obj.pick_id.address_id.country_id and  \
                                     package_obj.pick_id.address_id.country_id.code or "",
                'JointProductionIndicator': "",
                'NetCostCode': "NO",
                'PreferenceCriteria': "B",
                'ProducerInfo': produce,
                'MarksAndNumbers': "",
                'NumberOfPackagesPerCommodity': str(len(package_obj.pick_id.packages_ids)),
                'ProductWeight': {
                    'UnitOfMeasurement': {'Code': "LBS", 'Description': "Pounds"},
                    'Weight': "%.1f" % (tot_weight or 0.0)
                    },
                'VehicleID': "",
                }
            prods.append(product)
        return prods

    def create_comm_inv(self, cr, uid, package_obj):
        invoice_id = False
        if package_obj.pick_id.sale_id:
            if package_obj.pick_id.sale_id.invoice_ids:
                invoice_id = package_obj.pick_id.sale_id.invoice_ids[0]
        user = self.pool.get('res.users').browse(cr, uid, uid)
        comm_inv = {
            'FormType': "01",
            'Product': [],  # Placed out of this dictionary for common use
            'InvoiceNumber': "",
            'InvoiceDate': "",
            'PurchaseOrderNumber': "",
            'TermsOfShipment': "",
            'ReasonForExport': "SALE",
            'Comments': "",
            'DeclarationStatement': "I hereby certify that the good covered by this shipment qualifies as an originating good for purposes of \
                                     preferential tariff treatment under the NAFTA.",
            'CurrencyCode': user.company_id.currency_id.name or "",
            }
        if invoice_id:
            comm_inv['InvoiceNumber'] = invoice_id.number or '/'
            if invoice_id.date_invoice:
                d = invoice_id.date_invoice
                comm_inv['InvoiceDate'] = d[:4] + d[5:7] + d[8:10]
        if not comm_inv['InvoiceDate']:
            comm_inv['InvoiceDate'] = time.strftime("%Y%m%d")

        return comm_inv

    def create_cer_orig(self, cr, uid, package_obj):
        cer_orig = {
            'FormType': "03",
            'Product': [],  # Placed out of this dictionary for common use
            'ExportDate': time.strftime("%Y%m%d"),
            'ExportingCarrier': package_obj.pick_id.exp_carrier or "",
            }
        return cer_orig

    def get_value(self, cr, uid, object, message=None, context=None):

        if message is None:
            message = {}
        if message:
            try:
                from mako.template import Template as MakoTemplate
                message = tools.ustr(message)
                env = {
                    'user':self.pool.get('res.users').browse(cr, uid, uid, context=context),
                    'db':cr.dbname
                    }
                templ = MakoTemplate(message, input_encoding='utf-8')
                reply = MakoTemplate(message).render_unicode(object=object, peobject=object, env=env, format_exceptions=True)
                return reply or False
            except Exception:
                logging.exception("Can't render %r", message)
                return u""
        else:
            return message

    def create_ship_confirm_request_new(self, cr, uid, do, lines):
        if not do.shipper:
            return ''
        xml_ship_confirm_request = """<?xml version="1.0"?>
            <AccessRequest xml:lang='en-US'>
                <AccessLicenseNumber>%(access_l_no)s</AccessLicenseNumber>
                <UserId>%(user_id)s</UserId>
                <Password>%(password)s</Password>
            </AccessRequest>
            """ % {
               'access_l_no': do.shipper.accesslicensenumber or '',
               'user_id': do.shipper.userid or '',
               'password': do.shipper.password or '',
                }
        shipper_address_lines = ['', '', '']
        j = 0
        if do.shipper.address:
            if do.shipper.address.street:
                shipper_address_lines[j] = do.shipper.address.street
                j += 1
            if do.shipper.address.street2:
                shipper_address_lines[j] = do.shipper.address.street2
                j += 1
        shipto_address_lines = ['', '', '']
        j = 0
        if do.partner_id:
            if do.partner_id.name:
                shipto_address_lines[j] = do.partner_id.name
                j += 1
            if do.partner_id.street:
                shipto_address_lines[j] = do.partner_id.street
                j += 1
            if do.partner_id.street2:
                shipto_address_lines[j] = do.partner_id.street2
                j += 1

        xml_ship_confirm_request += """<?xml version="1.0"?>
            <ShipmentConfirmRequest>
                <Request>
                    <TransactionReference>
                        <CustomerContext>%(customer_context)s</CustomerContext>
                        <XpciVersion>1.0001</XpciVersion>
                    </TransactionReference>
                    <RequestAction>ShipConfirm</RequestAction>
                    <RequestOption>%(address_validate)s</RequestOption>
                </Request>
                <LabelSpecification>
                    <LabelPrintMethod>
                        <Code>%(lang_code)s</Code>
                        <Description>%(lang_name)s</Description>
                    </LabelPrintMethod>
                    <HTTPUserAgent></HTTPUserAgent>
                    <LabelImageFormat>
                        <Code>%(lang_code)s</Code>
                    </LabelImageFormat>
                    <LabelStockSize>
                        <Height>%(lab_height)s</Height>
                        <Width>%(lab_width)s</Width>
                    </LabelStockSize>
                </LabelSpecification>
                <Shipment>
                    <Description>%(shipment_description)s</Description>
                    <!--InvoiceLineTotal>
                        <CurrencyCode>%(invoice_currency_code)s</CurrencyCode>
                        <MonetaryValue>%(invoice_value)s</MonetaryValue>
                    </InvoiceLineTotal-->
                    <Shipper>
                        <Name>%(shipper_name)s</Name>
                        <AttentionName>%(shipper_attention_name)s</AttentionName>
                        <Address>
                            <AddressLine1>%(shipper_address_line1)s</AddressLine1>
                            <AddressLine2>%(shipper_address_line2)s</AddressLine2>
                            <AddressLine3>%(shipper_address_line3)s</AddressLine3>
                            <City>%(shipper_city)s</City>
                            <StateProvinceCode>%(shipper_state)s</StateProvinceCode>
                            <CountryCode>%(shipper_country)s</CountryCode>
                            <PostalCode>%(shipper_postal)s</PostalCode>
                        </Address>
                        <PhoneNumber>%(shipper_phone_number)s</PhoneNumber>
                        <ShipperNumber>%(shipper_number)s</ShipperNumber> 
                        <TaxIdentificationNumber>%(shipper_tax_id_number)s</TaxIdentificationNumber>
                        <FaxNumber>%(shipper_fax)s</FaxNumber>
                        <EMailAddress>%(shipper_email)s</EMailAddress>
                    </Shipper>
                    <ShipTo>
                        <CompanyName>%(shipto_company)s</CompanyName>
                        <AttentionName>%(shipto_attention_name)s</AttentionName>
                        <Address>
                            <AddressLine1>%(shipto_address_line1)s</AddressLine1>
                            <AddressLine2>%(shipto_address_line2)s</AddressLine2>
                            <AddressLine3>%(shipto_address_line3)s</AddressLine3>
                            <City>%(shipto_city)s</City>
                            <StateProvinceCode>%(shipto_state)s</StateProvinceCode>
                            <CountryCode>%(shipto_country)s</CountryCode>
                            <PostalCode>%(shipto_postal)s</PostalCode>
                        %(residential_address)s
                        </Address>
                        <PhoneNumber>%(shipto_phone_number)s</PhoneNumber>
                        <FaxNumber>%(shipto_fax)s</FaxNumber>
                        <EMailAddress>%(shipto_email)s</EMailAddress>
                        <TaxIdentificationNumber>%(shipto_tax_id_number)s</TaxIdentificationNumber>
                        <LocationID></LocationID>
                    </ShipTo>
                    <Service>
                        <Code>%(service_code)s</Code>
                        <Description>%(service_description)s</Description>
                    </Service>
               
                """ % {
                'customer_context': do.name or '',
                'address_validate': do.address_validate or 'nonvalidate',
                'lang_code': do.label_format_id.code or 'GIF',
                'lang_name': do.label_format_id.name or 'GIF',
                'lang_code': do.label_format_id.code or 'GIF',
                'lab_height': do.label_format_id.height or 0,
                'lab_width': do.label_format_id.width or 0,
                'shipment_description': do.note  or do.name or so.origin,
                'shipper_name': do.shipper.name or '',
                'shipper_attention_name': do.shipper.atten_name or '',
                'shipper_phone_number': do.shipper.address and do.shipper.address.phone or '',
                'shipper_number': do.shipper.acc_no or '',
                'shipper_tax_id_number': do.shipper.tax_id_no or '',
                'shipper_fax': do.shipper.address and do.shipper.address.fax or '' ,
                'shipper_email': do.shipper.address and do.shipper.address.email or '',
                'shipper_address_line1': shipper_address_lines[0],
                'shipper_address_line2': shipper_address_lines[1],
                'shipper_address_line3': shipper_address_lines[2],
                'shipper_city': do.shipper.address and do.shipper.address.city or '',
                'shipper_state': do.shipper.address and do.shipper.address.state_id and do.shipper.address.state_id.code or '',
                'shipper_country': do.shipper.address and do.shipper.address.country_id and do.shipper.address.country_id.code or '',
                'shipper_postal': do.shipper.address and do.shipper.address.zip or '',
                'shipto_company': do.partner_id.name or '',
                'shipto_attention_name': do.inv_att_name or '',
                'shipto_phone_number': do.partner_id.phone   or '',
                'shipto_fax': do.partner_id.fax or '',
                'shipto_email': do.partner_id.email or '' ,
                'shipto_tax_id_number': '',
                'shipto_address_line1': shipto_address_lines[0],
                'shipto_address_line2': shipto_address_lines[1],
                'shipto_address_line3': shipto_address_lines[2],
                'shipto_city': do.partner_id.city or '',
                'shipto_state': do.partner_id.state_id and do.partner_id.state_id.code or '',
                'shipto_country': do.partner_id.country_id and do.partner_id.country_id.code or '',
                'shipto_postal': do.partner_id.zip or '',
                'residential_address': do.partner_id.classification and do.partner_id.classification == '2' and '<ResidentialAddress/>' or '',
                'service_code': do.ups_service and do.ups_service.shipping_service_code or '',
                'service_description': do.ups_service and do.ups_service.description or '',
                'invoice_currency_code': do.sale_id and do.sale_id.pricelist_id.currency_id.name or 'USD',
                'invoice_value': do.sale_id and str(int(do.sale_id.amount_total)) or '',
                }
        if (do.ship_from and do.ship_from_address and do.ship_from_address.country_id.code == 'US' or do.shipper and \
            do.shipper.address and do.shipper.address.country_id and do.shipper.address.country_id.code == 'US') and \
            do.partner_id and do.partner_id.country_id.code in ('PR', 'CA'):
            xml_ship_confirm_request += """
                <InvoiceLineTotal>
                        <CurrencyCode>%(invoice_currency_code)s</CurrencyCode>
                        <MonetaryValue>%(invoice_value)s</MonetaryValue>
                    </InvoiceLineTotal>
                """ % {
                'invoice_currency_code': do.sale_id and do.sale_id.pricelist_id.currency_id.name or 'USD',
                'invoice_value': do.sale_id and str(int(do.sale_id.amount_untaxed)) or '',
                }
        if do.sat_delivery:
            xml_ship_confirm_request += """
            <ShipmentServiceOptions>
                <ShipmentNotification>
                   <SaturdayDelivery/>
                </ShipmentNotification>
            </ShipmentServiceOptions>
            """
        if do.ship_from:
            shipfrom_address_lines = ['', '', '']
            j = 0
            if do.ship_from_address:
                if do.ship_from_address.name:
                   shipfrom_address_lines[j] = do.ship_from_address.name
                   j += 1
                if do.ship_from_address.street:
                   shipfrom_address_lines[j] = do.ship_from_address.street
                   j += 1
                if do.ship_from_address.street2:
                   shipfrom_address_lines[j] = do.ship_from_address.street2
                   j += 1
            xml_ship_confirm_request += """
                 <ShipFrom>
                        <CompanyName>%(shipfrom_company)s</CompanyName>
                        <AttentionName>%(shipfrom_attention_name)s</AttentionName>
                        <Address>
                            <AddressLine1>%(shipfrom_address_line1)s</AddressLine1>
                            <AddressLine2>%(shipfrom_address_line2)s</AddressLine2>
                            <AddressLine3>%(shipfrom_address_line3)s</AddressLine3>
                            <City>%(shipfrom_city)s</City>
                             <StateProvinceCode>%(shipfrom_state)s</StateProvinceCode>
                            <CountryCode>%(shipfrom_country)s</CountryCode>
                            <PostalCode>%(shipfrom_postal)s</PostalCode>
                       </Address>
                        <PhoneNumber>%(shipfrom_phone_number)s</PhoneNumber>
                        <FaxNumber>%(shipfrom_fax)s</FaxNumber>
                        <EMailAddress>%(shipfrom_email)s</EMailAddress>
                        <TaxIdentificationNumber>%(shipfrom_tax_id_number)s</TaxIdentificationNumber>
                    </ShipFrom>
                """ % {
                'shipfrom_company': do.ship_from_address and do.ship_from_address and do.ship_from_address.name or '',
                'shipfrom_attention_name': '',
                'shipfrom_phone_number': do.ship_from_address and do.ship_from_address.phone or '',
                'shipfrom_fax': do.ship_from_address and do.ship_from_address.fax or '',
                'shipfrom_email': do.ship_from_address and do.ship_from_address.email or '',
                'shipfrom_tax_id_number': do.ship_from_tax_id_no or '',
                'shipfrom_address_line1': shipfrom_address_lines[0],
                'shipfrom_address_line2': shipfrom_address_lines[1],
                'shipfrom_address_line3': shipfrom_address_lines[2],
                'shipfrom_city': do.ship_from_address and do.ship_from_address.city or '',
                'shipfrom_state': do.ship_from_address and do.ship_from_address.state_id and do.ship_from_address.state_id.code or '',
                'shipfrom_country': do.ship_from_address and do.ship_from_address.country_id and do.ship_from_address.country_id.code or '',
                'shipfrom_postal': do.ship_from_address and do.ship_from_address.zip or '',
                }
        if do.comm_inv:
            soldto_address_lines = ['', '', '']
            j = 0
            if do.inv_address_id:
                if do.inv_address_id.name:
                    soldto_address_lines[j] = do.inv_address_id.name
                    j += 1
                if do.inv_address_id.street:
                    soldto_address_lines[j] = do.inv_address_id.street
                    j += 1
                if do.inv_address_id.street2:
                    soldto_address_lines[j] = do.inv_address_id.street2
                    j += 1
            xml_ship_confirm_request += """
                 <SoldTo>
                        <Option>%(soldto_option)s</Option>
                        <CompanyName>%(soldto_company)s</CompanyName>
                        <AttentionName>%(soldto_attention_name)s</AttentionName>
                        <PhoneNumber>%(soldto_phone_number)s</PhoneNumber>
                        <TaxIdentificationNumber>%(soldto_tax_id_number)s</TaxIdentificationNumber>
                        <Address>
                            <AddressLine1>%(soldto_address_line1)s</AddressLine1>
                            <AddressLine2>%(soldto_address_line2)s</AddressLine2>
                            <AddressLine3>%(soldto_address_line3)s</AddressLine3>
                            <City>%(soldto_city)s</City>
                            <StateProvinceCode>%(soldto_state)s</StateProvinceCode>
                            <CountryCode>%(soldto_country)s</CountryCode>
                            <PostalCode>%(soldto_postal)s</PostalCode>
                       </Address>
                    </SoldTo>
                """ % {
                'soldto_option': do.inv_option or '',
                'soldto_company': do.inv_company or '',
                'soldto_attention_name': do.inv_att_name or '',
                'soldto_phone_number': do.inv_address_id.phone or '',
                'soldto_tax_id_number': do.inv_tax_id_no or '',
                'soldto_address_line1': soldto_address_lines[0],
                'soldto_address_line2': soldto_address_lines[1],
                'soldto_address_line3': soldto_address_lines[2],
                'soldto_city': do.inv_address_id.city or '',
                'soldto_state': do.inv_address_id.state_id and do.inv_address_id.state_id.code or '',
                'soldto_country': do.inv_address_id.country_id and do.inv_address_id.country_id.code or '',
                'soldto_postal': do.inv_address_id.zip or '',
                }
        if not do.bill_shipping or do.bill_shipping == 'shipper':
            if not do.ups_use_cc:
                xml_ship_confirm_request += """
                <PaymentInformation>
                    <Prepaid>
                        <BillShipper>
                            <AccountNumber>%(bill_shipper_account_number)s</AccountNumber>
                        </BillShipper>
                    </Prepaid>
                </PaymentInformation>
                    """ % {
                    'bill_shipper_account_number': do.shipper.acc_no or '',
                    }
            else:
                cc_address_lines = ['', '', '']
                j = 0
                if do.ups_cc_address_id:
                    if do.ups_cc_address_id.name:
                        cc_address_lines[j] = do.ups_cc_address_id.name
                        j += 1
                    if do.ups_cc_address_id.street:
                        cc_address_lines[j] = do.ups_cc_address_id.street
                        j += 1
                    if do.ups_cc_address_id.street2:
                        cc_address_lines[j] = do.ups_cc_address_id.street2
                xml_ship_confirm_request += """
                <PaymentInformation>
                    <Prepaid>
                        <BillShipper>
                            <CreditCard>
                                <Type>%(cc_type)s</Type>
                                <Number>%(cc_number)s</Number>
                                <ExpirationDate>%(cc_exp_date)s</ExpirationDate>
                                <SecurityCode>%(cc_security_code)s</SecurityCode>
                                <Address>
                                    <AddressLine1>%(cc_address_line1)s</AddressLine1>
                                    <AddressLine2>%(cc_address_line2)s</AddressLine2>
                                    <AddressLine3>%(cc_address_line3)s</AddressLine3>
                                    <City>%(cc_city)s</City>
                                    <StateProvinceCode>%(cc_state)s</StateProvinceCode>
                                    <CountryCode>%(cc_country)s</CountryCode>
                                    <PostalCode>%(cc_postal)s</PostalCode>
                                </Address>
                            </CreditCard>
                        </BillShipper>
                    </Prepaid>
                </PaymentInformation>
                    """ % {
                    'cc_type': do.ups_cc_type or '',
                    'cc_number': do.ups_cc_number  or '',
                    'cc_exp_date': do.ups_cc_expiaration_date or '',
                    'cc_security_code': do.ups_cc_security_code or '',
                    'cc_address_line1': cc_address_lines[0],
                    'cc_address_line2': cc_address_lines[1],
                    'cc_address_line3': cc_address_lines[2],
                    'cc_city': do.ups_cc_address_id.city or '',
                    'cc_state': do.ups_cc_address_id.state_id and do.ups_cc_address_id.state_id.code or '',
                    'cc_country': do.ups_cc_address_id.country_id and do.ups_cc_address_id.country_id.code or '',
                    'cc_postal': do.ups_cc_address_id.zip or '',
                    }
        if do.bill_shipping == 'thirdparty':
            xml_ship_confirm_request += """
            <PaymentInformation>
                <ShipmentCharge>
                    <BillThirdParty>
                        <BillThirdPartyShipper>
                            <AccountNumber>%(thirdparty_account_number)s</AccountNumber>
                                <ThirdParty>
                                    <Address>
                                        <PostalCode>%(thirdparty_postal)s</PostalCode>
                                       <CountryCode>%(thirdparty_country)s</CountryCode>
                                    </Address>
                                </ThirdParty>
                        </BillThirdPartyShipper>
                    </BillThirdParty>
                   %(thirdparty_consignee_billed)s
                </ShipmentCharge>
            </PaymentInformation>
               """ % {
                'thirdparty_account_number': do.ups_third_party_account or '',
                'thirdparty_postal': do.ups_third_party_address_id and do.ups_third_party_address_id.zip or '' ,
                'thirdparty_country': do.ups_third_party_address_id and do.ups_third_party_address_id.country_id and \
                                      do.ups_third_party_address_id.country_id.code or '' ,
                'thirdparty_consignee_billed': do.ups_third_party_type == 'consignee' and  '<ConsigneeBilled/>' or '',
                }
        if do.bill_shipping == 'receiver':
            xml_ship_confirm_request += """
            <PaymentInformation>
                <FreightCollect>
                    <BillReceiver>
                        <AccountNumber>%(bill_receiver_account_number)s</AccountNumber>
                        <Address>
                            <PostalCode>%(bill_receiver_postal)s</PostalCode>
                        </Address>
                     </BillReceiver>
               </FreightCollect>
            </PaymentInformation>
               """ % {
                'bill_receiver_account_number': do.ups_bill_receiver_account or '',
                'bill_receiver_postal':  do.ups_bill_receiver_address_id.zip or '',
                }
#         for lines in do.packages_ids:
        xml_ship_confirm_request += """
            <Package>
                <Description>%(package_description)s</Description>
                <PackagingType>
                    <Code>%(packaging_type_code)s</Code>
                    <Description>%(packaging_type_description)s</Description>
                </PackagingType>
                <Dimensions>
                    <UnitOfMeasurement>
                        <Code>IN</Code>
                        <Description>Inches</Description>
                    </UnitOfMeasurement>
                    <Length>%(package_dimension_length)s</Length>
                    <Width>%(package_dimension_width)s</Width>
                    <Height>%(package_dimension_height)s</Height>
                </Dimensions>
                <PackageWeight>
                    <UnitOfMeasurement>
                        <Code>LBS</Code>
                        <Description>Pounds</Description>
                    </UnitOfMeasurement>
                    <Weight>%(package_dimension_weight)s</Weight>
                </PackageWeight>
                <PackageServiceOptions>
                    <InsuredValue>
                        <CurrencyCode>USD</CurrencyCode>
                        <MonetaryValue>%(package_insured_value)s</MonetaryValue>
                    </InsuredValue>
                </PackageServiceOptions>
                """ % {
            'package_description': lines.description or '',
            'packaging_type_code': lines.package_type.code or '',
            'packaging_type_description': lines.package_type.name or '',
            'package_dimension_length':  str(lines.length) or '',
            'package_dimension_width': str(lines.width) or '',
            'package_dimension_height': str(lines.height) or '',
            'package_dimension_weight': str(lines.weight) or '',
            'package_insured_value': str(lines.decl_val) or '',
            }
                
        if (do.ship_from_address and do.ship_from_address.country_id and do.ship_from_address.country_id.code and (do.ship_from_address.country_id.code=='US') and do.partner_id.country_id and do.partner_id.country_id.code and do.partner_id.country_id.code == 'US')\
            or (do.ship_from_address and do.ship_from_address.country_id and do.ship_from_address.country_id.code and (do.ship_from_address.country_id.code=='PR') and do.partner_id.country_id and do.partner_id.country_id.code and do.partner_id.country_id.code == 'PR'):        
            xml_ship_confirm_request += """       
                <ReferenceNumber>
                    <Code>01</Code>
                    <Value>%(package_reference_value1)s</Value>
                </ReferenceNumber>
                <ReferenceNumber>
                    <Code>02</Code>
                    <Value>%(package_reference_value2)s</Value>
                </ReferenceNumber>
           
            """ % {
            'package_reference_code1': lines.ref1 or '',
            'package_reference_value1': lines.ref2 or '',
            'package_reference_code2': lines.ref2_code or '',
            'package_reference_value2': lines.ref2_number or '',
         }
            
        xml_ship_confirm_request += """ 
            </Package>
            </Shipment>
            </ShipmentConfirmRequest>"""
        return xml_ship_confirm_request

    def process_ship(self, cr, uid, ids, context=None):
        package_obj = self.pool.get('stock.packages')
        deliv_order = self.browse(cr, uid, type(ids) == type([]) and ids[0] or ids, context=context)
        if deliv_order.ship_company_code != 'ups':
            return super(stock_picking, self).process_ship(cr, uid, ids, context=context)
        error_flag = False
        ship_move_ids = {}
        do_transaction = True
        response_dic = {}
        if not (deliv_order.logis_company or deliv_order.shipper or deliv_order.ups_service):
            raise osv.except_osv("Warning", "Please select Logistics Company, Shipper and Shipping Service")
        if not deliv_order.packages_ids:
            raise osv.except_osv("Warning", "Please add shipping packages before doing Process Shipping.")
        if deliv_order.sale_id and deliv_order.sale_id.order_policy == 'credit_card' and not deliv_order.sale_id.invoiced:
            if not deliv_order.sale_id.cc_pre_auth:
                raise osv.except_osv("Warning", "The sales order is not paid")
            else:
                do_transaction = False
                rel_voucher_id = deliv_order.sale_id.rel_account_voucher_id
                if rel_voucher_id and rel_voucher_id.state != 'posted' and deliv_order.sale_id.cc_pre_auth:
                    vals_vouch = {'cc_p_authorize': False, 'cc_charge': True}
                    if 'trans_type' in rel_voucher._columns.keys():
                        vals_vouch.update({'trans_type': 'PriorAuthCapture'})
                    self.pool.get('account.voucher').write(cr, uid, [rel_voucher_id.id], vals_vouch, context=context)
                    do_transaction = self.pool.get('account.voucher').authorize(cr, uid, [rel_voucher_id.id], context=context)
            if  not do_transaction:
                self.write(cr, uid, ids, {'ship_state': 'hold', 'ship_message': 'Unable to process creditcard payment.'}, context=context)
                cr.commit()
                raise osv.except_osv(_('Final credit card charge cannot be completed!'), _("Please hold shipment and contact customer service.."))
        warning_error = False
        status = 0
        if deliv_order:
            packages = 0
            for lines in deliv_order.packages_ids:
                ship_confirm_request_xml = self.create_ship_confirm_request_new(cr, uid, deliv_order, lines)
                ship_confirm_web = ''
                ship_confirm_port = ''
                if deliv_order.logis_company:
                    if deliv_order.logis_company.test_mode:
                        ship_confirm_web = deliv_order.logis_company.ship_req_test_web
                        ship_confirm_port = deliv_order.logis_company.ship_req_test_port
                    else:
                        ship_confirm_web = deliv_order.logis_company.ship_req_web
                        ship_confirm_port = deliv_order.logis_company.ship_req_port
                    if ship_confirm_web:
                        parse_url = urlparse(ship_confirm_web)
                        serv = parse_url.netloc
                        serv_path = parse_url.path
                    else:
                        raise osv.except_osv(_('Unable to find Shipping URL!'), _("Please configure the shipping company with websites."))
                    conn = httplib.HTTPSConnection(serv, ship_confirm_port)
                    res = conn.request("POST", serv_path, ship_confirm_request_xml)
                    """1.make and call function to send request/ 2.make function to process the response and write it """
                    res = conn.getresponse()
                    result = res.read()
    #                 result[:result.find('PUBLIC')+ len('PUBLIC')]+''+result[result.find('PUBLIC')+ len('PUBLIC'):]
                    response_dic = xml2dic.main(result)
                    response = ''
                    status_description = ''
                    status = 0
                    context.update({'error_message': None})
                    if response_dic:
                        for elm in response_dic['ShipmentConfirmResponse']:
                            if elm.get('Response'):
                                for rep in elm['Response']:
                                    if rep.get('ResponseStatusDescription'):
                                        status_description = rep['ResponseStatusDescription']
                                    if rep.get('ResponseStatusCode'):
                                        if rep['ResponseStatusCode'] == '1':
                                            status = 1
                                    if rep.get('Error'):
                                        for err in rep['Error']:
                                            if err.get('ErrorDescription'):
                                                context.update({'error_message':err.get('ErrorDescription')})
                                                status_description += ': ' + err.get('ErrorDescription')
                    
                    package_obj.write(cr, uid, lines.id, {'ship_message': status_description})
                    
                    if not status:
                        deliv_order.write({'ship_message' : status_description })
                        
                    else:
                        shipment_identification_number = ''
                        shipment_digest = ''
                        for elm in response_dic['ShipmentConfirmResponse']:
                            if elm.get('ShipmentIdentificationNumber'):
                                shipment_identification_number = elm['ShipmentIdentificationNumber']
                                break
                        for elm in response_dic['ShipmentConfirmResponse']:
                            if elm.get('ShipmentDigest'):
                                shipment_digest = elm['ShipmentDigest']
                                break
                        deliv_order.write({'shipment_digest': shipment_digest, 'shipment_identific_no': shipment_identification_number, }, context=context)
                        do = self.browse(cr, uid, deliv_order.id, context=context)
                        sh_accept = self.process_ship_accept(cr, uid, do, packages, context=context) 
                        status = sh_accept[0]
                        label_code = sh_accept[1]
                packages += 1
                           
            if status:
                try:
                    self.send_conf_mail(cr, uid, do.id, context=context)
                except Exception, e:
                    pass
                if label_code == 'GIF':
                    return {
                        'type': 'ir.actions.report.xml',
                        'report_name': 'multiple.label.print',
                        'datas': {
                            'model': 'stock.picking',
                            'id': ids and ids[0] or False,
                            'ids': ids and ids or [],
                            'report_type': 'pdf'
                            },
                        'nodestroy': True
                        }
            return status
        return False

    def _get_journal_id(self, cr, uid, ids, context=None):
        journal_obj = self.pool.get('account.journal')
        vals = []
        for pick in self.browse(cr, uid, ids, context=context):
            src_usage = pick.move_lines[0].location_id.usage
            dest_usage = pick.move_lines[0].location_dest_id.usage
            type = pick.type
            if type == 'out' and dest_usage == 'supplier':
                journal_type = 'purchase_refund'
            elif type == 'out' and dest_usage == 'customer':
                journal_type = 'sale'
            elif type == 'in' and src_usage == 'supplier':
                journal_type = 'purchase'
            elif type == 'in' and src_usage == 'customer':
                journal_type = 'sale_refund'
            else:
                journal_type = 'sale'
            value = journal_obj.search(cr, uid, [('type', '=', journal_type)], context=context)
            for jr_type in journal_obj.browse(cr, uid, value, context=context):
                t1 = jr_type.id, jr_type.name
                if t1 not in vals:
                    vals.append(t1)
        return vals

    def do_partial(self, cr, uid, ids, partial_datas, context=None):
        res = self._get_journal_id(cr, uid, ids, context=context)
        result_partial = super(stock_picking, self).do_partial(cr, uid, ids, partial_datas, context=context)
        if res and res[0]:
            journal_id = res[0][0]
            result = result_partial
            for picking_obj in self.browse(cr, uid, ids, context=context):
                sale = picking_obj.sale_id
                if sale and sale.order_policy == 'picking':
                    pick_id = result_partial[picking_obj.id]['delivered_picking']
                    result = self.action_invoice_create(cr, uid, [pick_id], journal_id, type=None, context=context)
                    inv_obj = self.pool.get('account.invoice')
                    if result:
                        inv_obj.write(cr, uid, result.values(), {
                           'ship_service': sale.ship_service,
                           'shipcharge': sale.shipcharge,
                           'sale_account_id': sale.ship_method_id and sale.ship_method_id.account_id and \
                                              sale.ship_method_id.account_id.id or False,
#                           'ship_method_id': sale.ship_method_id and sale.ship_method_id.id
                           })
                        inv_obj.button_reset_taxes(cr, uid, result.values(), context=context)
        return result_partial
    
    
    def get_rate(self, cr, uid, ids, context=None):
        
        pick_obj = self.pool.get('sale.order')
        
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
        weight = data.weight_net or 0.00
        
#         invoice = self.pool.get('account.invoice').browse(cr, uid, context['active_id'], context=context)
#         weight = invoice.total_weight_net or 0.00
        receipient_zip = data.partner_id and data.partner_id.zip or ''
        receipient_country_code = data.partner_id.country_id and data.partner_id.country_id.code or ''
        access_license_no = data.shipper and  data.shipper.accesslicensenumber or ''
        user_id = data.shipper and  data.shipper.userid or ''
        password = data.shipper and data.shipper.password or ''
        pickup_type_ups = data.ups_pickup_type
        shipper_zip = data.shipper and data.shipper.address and data.shipper.address.zip or ''
        shipper_country_code =  data.shipper and data.shipper.address and  data.shipper.address.country_id and \
                                data.shipper.address.country_id.code or ''
        ups_info_shipper_no = data.shipper and data.shipper.acc_no or ''
        
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
                pick_obj.write(cr,uid,so,{'shipcharge':amount or 0.00,'ups_service_id':ups_service_id,'status_message':warning},context=context)
        
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

stock_picking()

class stock(osv.osv_memory):
    
    _inherit = "stock.invoice.onshipping"
    
    def create_invoice(self, cr, uid, ids, context=None):
        if context is None:
            context = {}
        invoice_ids = []
        res = super(stock, self).create_invoice(cr, uid, ids, context=context)
        invoice_ids += res.values()
        picking_pool = self.pool.get('stock.picking.out')
        invoice_pool = self.pool.get('account.invoice')
        active_picking = picking_pool.browse(cr, uid, context.get('active_id', False), context=context)
        if active_picking:
            invoice_pool.write(cr, uid, invoice_ids, {'shipcharge':active_picking.shipcharge }, context=context)
        return res
stock()

class stock_move(osv.osv):
    
    _inherit = "stock.move"
    
    def created(self, cr, uid, vals, context=None):
        if not context: context = {}
        package_obj = self.pool.get('stock.packages')
        pack_id = None
        package_ids = package_obj.search(cr, uid, [('pick_id', "=", vals.get('picking_id'))])
        if vals.get('picking_id'):
            rec = self.pool.get('stock.picking').browse(cr, uid, vals.get('picking_id'), context)
            if not context.get('copy'):
                if not package_ids:
                    pack_id = package_obj.create(cr, uid , {'package_type': rec.sale_id.ups_packaging_type.id, 'pick_id': vals.get('picking_id')})
        res = super(stock_move, self).create(cr, uid, vals, context)
        if not context.get('copy'):
            context.update({'copy': 1})
            default_vals = {}
            if pack_id:
                default_vals = {'package_id':pack_id, 'picking_id':[]}
            elif package_ids:
                default_vals = {'package_id':package_ids[0], 'picking_id':[]}
            self.copy(cr, uid, res, default_vals , context)
        return res
    
stock_move()
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
