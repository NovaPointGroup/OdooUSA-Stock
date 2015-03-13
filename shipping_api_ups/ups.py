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
import httplib
from xml.dom.minidom import Document
import xml2dic
from openerp.tools.translate import _

class ups_account_shipping(osv.osv):
    
    _name = "ups.account.shipping"

    _columns = {
        'name': fields.char('Name', size=64, required=True),
        'ups_account_id': fields.many2one('ups.account', 'UPS Account', required=True),
        'accesslicensenumber': fields.related('ups_account_id', 'accesslicensenumber', type='char', size=64, string='AccessLicenseNumber', required=True),
        'userid': fields.related('ups_account_id', 'userid', type='char', size=64, string='UserId', required=True),
        'password': fields.related('ups_account_id', 'password', type='char', size=64, string='Password', required=True),
        'active': fields.related('ups_account_id', 'ups_active', string='Active', type='boolean'),
        'acc_no': fields.related('ups_account_id', 'acc_no', type='char', size=64, string='Account Number', required=True),
        'atten_name': fields.char('AttentionName', size=64, required=True, select=1),
        'tax_id_no': fields.char('Tax Identification Number', size=64 , select=1, help="Shipper's Tax Identification Number."),
        'logistic_company_id': fields.many2one('logistic.company', 'Parent Logistic Company'),
        'delivery_mthd_id': fields.many2one('delivery.method', 'Parent Delivery Method'),
#         'ups_shipping_service_ids': fields.one2many('ups.shipping.service.type', 'ups_account_id', 'Shipping Service'),
        'ups_shipping_service_ids':fields.many2many('ups.shipping.service.type', 'shipping_service_rel', 'ups_account_id', 'service_id', 'Shipping Service'),
        'address': fields.property(
           type='many2one',
           relation='res.partner',
           string="Ship From Address",
           view_load=True),
        'trademark': fields.char('Trademark', size=1024, select=1),
        'company_id': fields.many2one('res.company', 'Company'),
        'partner_id': fields.many2one('res.partner', 'Transport Company', required=True, help="The UPS account contact information and and address"),

    }
    _defaults = {
        'active': True
    }
    
    def onchange_ups_account(self, cr, uid, ids, ups_account_id=False, context=None):
        res = {
            'accesslicensenumber': '',
            'userid': '',
            'password': '',
            'active': True,
            'acc_no': ''
            }
        
        if ups_account_id:
            ups_account = self.pool.get('ups.account').browse(cr, uid, ups_account_id, context=context)
            res = {
                'accesslicensenumber': ups_account.accesslicensenumber,
                'userid': ups_account.userid,
                'password': ups_account.password,
                'active': ups_account.ups_active,
                'acc_no': ups_account.acc_no
                }
        return {'value': res}

ups_account_shipping()

class ups_account_shipping_service(osv.osv):
    
    _name = "ups.shipping.service.type"
    _rec_name = "description"
    
    _columns = {
        'description': fields.char('Description', size=32, required=True, select=1),
        'category': fields.char('Category', size=32, select=1),
        'shipping_service_code': fields.char('Shipping Service Code', size=8, select=1),
        'rating_service_code': fields.char('Rating Service Code', size=8, select=1),
        'ups_account_id': fields.many2one('ups.account.shipping', 'Parent Shipping Account'),
        
        'common':fields.boolean("Common?",help="Is Service Applicable for both domestic or international ups shippings"),
        'is_intnl':fields.boolean("International?",help="Service Applicable for International ups shippings or Domestic if unchecked"),
        }
    
ups_account_shipping_service()

class delivery_method(osv.osv):
    _inherit = "delivery.method"
    
    def _get_company_code(self, cr, user, context=None):
        res =  super(delivery_method, self)._get_company_code(cr, user, context=context)
        res.append(('ups', 'UPS'))
        return res
    
    _columns={
                'ship_company_code': fields.selection(_get_company_code, 'Type', method=True, required=True, size=64),
                'ship_req_web': fields.char('Ship Request Website', size=256 ),
                'ship_req_port': fields.integer('Ship Request Port'),
                'ship_req_test_web': fields.char('Test Ship Request Website', size=256 ),
                'ship_req_test_port': fields.integer('Test Ship Request Port'),
                'ship_accpt_web': fields.char('Ship Accept Website', size=256 ),
                'ship_accpt_port': fields.integer('Ship Accept Port' ),
                'ship_accpt_test_web': fields.char('Test Ship Accept Website', size=256),
                'ship_accpt_test_port': fields.integer('Test Ship Accept Port'),
                'ship_void_web': fields.char('Ship Void Website', size=256),
                'ship_void_port': fields.integer('Ship Void Port'),
                'ship_void_test_web': fields.char('Test Ship Void Website', size=256),
                'ship_void_test_port': fields.integer('Test Ship Void Port'),
                'ship_rate_web': fields.char('Ship Rate Website', size=256 ),
                'ship_rate_port': fields.integer('Ship Rate Port'),
                'ship_rate_test_web': fields.char('Test Ship Rate Website', size=256 ),
                'ship_rate_test_port': fields.integer('Test Ship Rate Port'),
                'ship_tracking_url': fields.char('Tracking URL', size=256),
               'ups_shipping_account_ids': fields.one2many('ups.account.shipping', 'delivery_mthd_id', 'Shipping Account'),
               'test_mode': fields.boolean('Test Mode'),
               'url': fields.char('Website',size=256 , select=1),
               'company_id': fields.many2one('res.company', 'Company'),
#               'ship_account_id': fields.property(
#               'account.account',
#               type='many2one',
#               relation='account.account',
#               string="Cost Account",
#               view_load=True),
            'note': fields.text('Notes'),
              }
    _defaults = {
        'ship_req_web': "https://onlinetools.ups.com/webservices/shipconfirm",
        'ship_req_port': 443,
        'ship_req_test_web': "https://wwwcie.ups.com/ups.app/xml/ShipConfirm",
        'ship_req_test_port': 443,
        'ship_accpt_web': "https://onlinetools.ups.com/ups.app/ShipAccept",
        'ship_accpt_port': 443,
        'ship_accpt_test_web': "https://wwwcie.ups.com/ups.app/xml/ShipAccept",
        'ship_accpt_test_port': 443,
        'ship_void_web': "https://onlinetools.ups.com/xml/ups.app/void",
        'ship_void_port': 443,
        'ship_void_test_web': "https://wwwcie.ups.com/ups.app/xml/Void",
        'ship_void_test_port': 443,
        'ship_rate_web': "https://onlinetools.ups.com/ups.app/xml/Rate",
        'ship_rate_port': 443,
        'ship_rate_test_web': "https://wwwcie.ups.com/ups.app/xml/Rate",
        'ship_rate_test_port': 443,
        'ship_tracking_url': "https://wwwapps.ups.com/WebTracking/processInputRequest?sort_by=status&tracknums_displayed=1&TypeOfInquiryNumber=T&loc=en_US&InquiryNumber1=%s&track.x=0&track.y=0",
                 }
    
    def onchange_shipping_number(self, cr, uid, ids, shipping_no, url, context=None):
        ret = {}
        if url:
            b = url[url.rindex('/'): len(url)]
            b = b.strip('/')
            if re.match("^[0-9]*$", b):
                url = url[0:url.rindex('/')]
            url += ('/' + shipping_no)
            ret['url'] = url
        return{'value': ret}
        
delivery_method()

class ups_account(osv.osv):
    '''
        UPS Account details
    '''
    _name = "ups.account"

    _rec_name = "accesslicensenumber"

    _columns = {
        'accesslicensenumber': fields.char('AccessLicenseNumber', size=32, required=True, select=1),
        'userid': fields.char('UserId',size=64 , required=True, select=1),
        'password': fields.char('Password', size=64, required=True, select=1),
        'ups_active':fields.boolean('Active', size=64,),
        'url':fields.char('Server',size=64 , required=True, select=1),
        'acc_no':fields.char('Account Number',size=64 , required=True, select=1),
        'max_lim_size':fields.integer('Maximum List Size',required=True,)
    }

    _defaults = {
        'url': lambda *a: 'wwwcie.ups.com',
        'ups_active':lambda *a: True,
        'max_lim_size':lambda *a:10,
    }

    def _create_Address_Validation_Request_xml(self,cr, uid, data_for_Address_Validation_Request,data_for_Access_Request):
        """Creates  and returns the xml request to be sent address validation API """
        doc1 = Document()
        AccessRequest = doc1.createElement("AccessRequestxml")
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

        doc = Document()

        #creating AddressValidationRequest tag
        AddressValidationRequest = doc.createElement("AddressValidationRequest")
        AddressValidationRequest.setAttribute("xml:lang", "en-US")
        doc.appendChild(AddressValidationRequest)

        #creating Request tag XMLpath=/AddressValidationRequest/Request
        Request = doc.createElement("Request")
        AddressValidationRequest.appendChild(Request)

        #creating TransactionReference tag XMLpath=AddressValidationRequest/Request/TransactionReference
        TransactionReference = doc.createElement("TransactionReference")
        Request.appendChild(TransactionReference)

        #creating CustomerContext tag XMLpath=/AddressValidationRequest/Request/TransactionReference/CustomerContext
        CustomerContext = doc.createElement("CustomerContext")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['Request']['Transaction Reference']["CustomerContext"])
        CustomerContext.appendChild(ptext)
        TransactionReference.appendChild(CustomerContext)

        #creating XpciVersion tag XMLpath=AddressValidationRequest/Request/TransactionReference/XpciVersion
        XpciVersion = doc.createElement("XpciVersion")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['Request']['Transaction Reference']["XpciVersion"])
        XpciVersion.appendChild(ptext)
        TransactionReference.appendChild(XpciVersion)

        #creating ToolVersion tag XMLpath=AddressValidationRequest/Request/TransactionReference/ToolVersion
        ToolVersion = doc.createElement("ToolVersion")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['Request']['Transaction Reference']["ToolVersion"])
        ToolVersion.appendChild(ptext)
        TransactionReference.appendChild(ToolVersion)

        #creating RequestAction tag XMLpath=AddressValidationRequest/Request/RequestAction
        RequestAction = doc.createElement("RequestAction")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['Request']["RequestAction"])
        RequestAction.appendChild(ptext)
        Request.appendChild(RequestAction)

        #creating RequestOption tag XMLpath=AddressValidationRequest/Request/RequestOption
        RequestOption = doc.createElement("RequestOption")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['Request']["RequestOption"])
        RequestOption.appendChild(ptext)
        Request.appendChild(RequestOption)

        #creating RequestOption tag XMLpath=AddressValidationRequest/MaximumListSize
        MaximumListSize = doc.createElement("MaximumListSize")
        ptext = doc.createTextNode(data_for_Address_Validation_Request["MaximumListSize"])
        MaximumListSize.appendChild(ptext)
        AddressValidationRequest.appendChild(MaximumListSize)

        #creating AddressKeyFormat tag    XMLpath=AddressValidationRequest/AddressKeyFormat
        AddressKeyFormat = doc.createElement("AddressKeyFormat")
        AddressValidationRequest.appendChild(AddressKeyFormat)

        #creating ConsigneeName tag    XMLpath=AddressValidationRequest/AddressKeyFormat/ConsigneeName
        ConsigneeName = doc.createElement("ConsigneeName")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["ConsigneeName"])
        ConsigneeName.appendChild(ptext)
        AddressKeyFormat.appendChild(ConsigneeName)

        #creating BuildingName tag    XMLpath=AddressValidationRequest/AddressKeyFormat/BuildingName
        BuildingName = doc.createElement("BuildingName")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["BuildingName"])
        BuildingName.appendChild(ptext)
        BuildingName.appendChild(BuildingName)

        #creating AddressLine tag    XMLpath=AddressValidationRequest/AddressKeyFormat/AddressLine
        AddressLine = doc.createElement("AddressLine")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["AddressLine1"])
        AddressLine.appendChild(ptext)
        AddressKeyFormat.appendChild(AddressLine)

        AddressLine = doc.createElement("AddressLine")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["AddressLine2"])
        AddressLine.appendChild(ptext)
        AddressKeyFormat.appendChild(AddressLine)

        #creating Region tag    XMLpath=AddressValidationRequest/AddressKeyFormat/Region
        Region = doc.createElement("Region")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["Region"])
        Region.appendChild(ptext)
        AddressKeyFormat.appendChild(Region)

        #creating PoliticalDivision2 tag XMLpath=AddressValidationRequest/AddressKeyFormat/PoliticalDivision2
        PoliticalDivision2 = doc.createElement("PoliticalDivision2")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["PoliticalDivision2"])
        PoliticalDivision2.appendChild(ptext)
        AddressKeyFormat.appendChild(PoliticalDivision2)

        #creating PoliticalDivision1 tag XMLpath=AddressValidationRequest/AddressKeyFormat/PoliticalDivision1
        PoliticalDivision1 = doc.createElement("PoliticalDivision1")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["PoliticalDivision1"])
        PoliticalDivision1.appendChild(ptext)
        AddressKeyFormat.appendChild(PoliticalDivision1)

        #creating PostcodePrimaryLow tag XMLpath=AddressValidationRequest/AddressKeyFormat/PostcodePrimaryLow
        PostcodePrimaryLow = doc.createElement("PostcodePrimaryLow")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["PostcodePrimaryLow"])
        PostcodePrimaryLow.appendChild(ptext)
        AddressKeyFormat.appendChild(PostcodePrimaryLow)

        #creating PostcodeExtendedLow tag XMLpath=AddressValidationRequest/AddressKeyFormat/PostcodeExtendedLow
        PostcodeExtendedLow = doc.createElement("PostcodeExtendedLow")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["PostcodeExtendedLow"])
        PostcodeExtendedLow.appendChild(ptext)
        AddressKeyFormat.appendChild(PostcodeExtendedLow)

    #creating PostcodeExtendedLow tag XMLpath=AddressValidationRequest/AddressKeyFormat/Urbanization
        Urbanization = doc.createElement("Urbanization")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["Urbanization"])
        Urbanization.appendChild(ptext)
        AddressKeyFormat.appendChild(Urbanization)

    #creating CountryCode tag XMLpath=AddressValidationRequest/AddressKeyFormat/CountryCode
        CountryCode = doc.createElement("CountryCode")
        ptext = doc.createTextNode(data_for_Address_Validation_Request['AddressKeyFormat']["CountryCode"])
        CountryCode.appendChild(ptext)
        AddressKeyFormat.appendChild(CountryCode)

        Request_string1=doc1.toprettyxml()
        Request_string2=doc.toprettyxml()
        Request_string=Request_string1+Request_string2
        return Request_string

    def _create_https_connecetion(self,cr, uid, UPS_SERVER,Request_string,UPS_url="/ups.app/xml/XAV", default_port=443, context={}):
        """Connects to the UPS server and returns the response as xml string """
        conn=httplib.HTTPSConnection(UPS_SERVER,default_port)    #creating http connection

        if not conn:
            response_data='Connection failed'
        else:
            try:
                conn.request("POST",UPS_url,Request_string)    #requst being sent to ups
                response = conn.getresponse()
            except Exception:
                response_data='Connection failed'
            else:
                response_data = response.read()
        return response_data

    def address_validation(self,cr, uid, address_id, context={}):
        """ This function is called from the wizard.Performs the actual computing in address validation """
        status="True"
        error_msg=""
        ups_ids=self.pool.get('ups.account').search(cr, uid,[('ups_active',"=",True)])
        if ups_ids and address_id:
            ups_account = self.pool.get('ups.account').browse(cr, uid, ups_ids[0], context=context)
            if type(address_id) is list or type(address_id) is tuple:
                address_id=address_id[0]
            address = self.pool.get('res.partner').browse(cr, uid, address_id, context=context)

            data_for_Access_Request={
                        'AccessLicenseNumber':ups_account.accesslicensenumber,
                        'UserId':ups_account.userid,
                        'Password':ups_account.password
                    }
            data_for_Address_Validation_Request={
                            'Request':{
                                   'Transaction Reference':{
                                                'CustomerContext':"",
                                                'XpciVersion':"1.0001",
                                                'ToolVersion':"",
                                                },
                                   'RequestAction':"XAV",
                                   'RequestOption':"3",
                                  },
                            'RegionalRequestIndicator':"",
                            'MaximumListSize':str(ups_account.max_lim_size),
                            'AddressKeyFormat':{
                                        'ConsigneeName':address.name or "",
                                        'BuildingName':"",
                                        'AddressLine1':str(address.street or ""),
                                        'AddressLine2':str(address.street2 or ""),
                                        'Region':"",
                                        'PoliticalDivision2':str(address.city or ""),
                                        'PoliticalDivision1':str(address.state_id and address.state_id.code),
                                        'PostcodePrimaryLow':str(address.zip or ""),
                                        'PostcodeExtendedLow':"",
                                        'Urbanization':"",
                                        'CountryCode':"US"
                                        }
                            }
            Request_string=self._create_Address_Validation_Request_xml(cr, uid, data_for_Address_Validation_Request,data_for_Access_Request)
            response_string=self._create_https_connecetion(cr,uid,ups_account.url,Request_string)
            if response_string == 'Connection failed':
                        addr_status=False
                        error_msg='Connection to server failed'
                        ret_list=[]
            else:
                        response_dic=xml2dic.main(response_string)
                        response=response_dic['AddressValidationResponse'][0]['Response']
                        ret_list=[]
                        street1=""
                        street2=""
                        city=""
                        state=""
                        zip=""
                        country_code=""
                        
                        status_description = ''
            
                        for i in range(3,16):
                           
                            if  len(response_dic['AddressValidationResponse']) > i  and response_dic['AddressValidationResponse'][i] :
                                
                                classification = str(response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][0]['AddressClassification'][0]['Code'])
                                j=1
                                if response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j].get('AddressLine'):
                                    street1=response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j]['AddressLine']
                                j+=1
                                if response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j].has_key('AddressLine'):
                                    street2=response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j]['AddressLine']
                                    j+=1

                                if response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j].has_key('Region'):
                                    street2=response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j]['Region']
                                j+=1

                                if response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j].has_key('PoliticalDivision2'):
                                   city=response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j]['PoliticalDivision2']
                                j+=1

                                if response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j].has_key('PoliticalDivision1'):
                                   state=response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j]['PoliticalDivision1']
                                j+=1
                                if response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j].get('PostcodePrimaryLow'):
                                   zip=response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j]['PostcodePrimaryLow']
                                j+=2
                                if response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j].get('CountryCode'):
                                   country_code=response_dic['AddressValidationResponse'][i]['AddressKeyFormat'][j]['CountryCode']
                                
                                addr_dict = {
                                                 'street1':street1,
                                                 'city':city,
                                                'state':state,
                                                  'zip':zip,
                                                  'classification' : classification
                                                       }
                                if addr_dict not in ret_list and (addr_dict['street1'] or addr_dict['city'] or addr_dict['state'] or addr_dict['zip']):
                                    ret_list.append(addr_dict)
                        response_status=response_dic['AddressValidationResponse'][0]['Response'][1]['ResponseStatusCode']
                        if response_status == '1':
                            if ret_list:
                                if (len(ret_list) == 1) and (ret_list[0].get('street1','').upper() == str(address.street).upper()):
                                    error_msg="Success:The address is valid"
                                else:
                                    error_msg="Please review the suggested address."
                                addr_status = True
                            else:
                                error_msg="Success:No match found"
                                addr_status = False
                        elif response_status == '0':
                            addr_status=False
                            error_msg=response_dic['AddressValidationResponse'][0]['Response'][3]['Error'][2]['ErrorDescription']
                        if response_dic['AddressValidationResponse'][0]['Response'][1]['ResponseStatusCode'] == '0':
                                error_msg = 'Error : '+ error_msg
                
            vals = {'addr_status':addr_status,
                    'error_msg':error_msg,
                    'address_list':ret_list}
            
            return vals

        else:
            raise osv.except_osv(_('Warning !'), _('Address validation is not set up.'))
            return []

ups_account()

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
