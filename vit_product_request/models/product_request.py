from odoo import tools
from odoo import fields,models,api
import time
import logging
from odoo.tools.translate import _
from collections import defaultdict
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)
PR_STATES =[('draft','Draft'),
    ('open','Confirmed'), 
    ('onprogress','On Progress'), 
    ('done','Done'),
    ('reject','Rejected')]
PR_LINE_STATES =[('draft','Draft'),
    ('open','Confirmed'), 
    ('onprogress','On Progress'), # Call for Bids in progress
    ('done','Done'),# Call for Bids = PO created / done
    ('reject','Rejected')]


class ProductRequest(models.Model):
    _name           = "vit.product.request"
    _inherit        = ['mail.thread']
    _order             = "name desc"


    @api.multi
    def unlink(self):
        for data in self:
            if data.state != 'draft':
                raise UserError(_('Data yang bisa dihapus hanya yang berstatus draft !'))
        return super(ProductRequest, self).unlink()

    def _product_request_lines(self):
        results = {}
        # return harus berupa dictionary dengan key id session
        # contoh kalau 3 records:
        # {
        #      1 : 50.8,
        #      2 : 25.5,
        #      3 : 10.0
        # }

        for pr in self.browse():
            product_names = []
            for line in pr.product_request_line_ids:
                if line.product_id.name:
                    product_names.append(line.product_id.name)
            results[pr.id] = ",".join(product_names)
        return results

    @api.model
    def _get_default_department_id(self):
        employee = self.env['hr.employee'].sudo().search([('user_id','=',self._uid)])
        if employee and employee.department_id:
            return employee.department_id.id

    @api.model
    def _get_default_warehouse_id(self):
        employee = self.env['hr.employee'].sudo().search([('user_id','=',self._uid)])
        if employee and employee.department_id and employee.department_id.warehouse_id:
            return employee.department_id.warehouse_id.id

    name = fields.Char("Number" , readonly=True)
    date =  fields.Date("Request Date",
        required=True,
        readonly=True,
        default=lambda *a : time.strftime("%Y-%m-%d"),
        states={'draft':[('readonly',False)]},
        track_visibility='onchange'
    )
    user_id = fields.Many2one(comodel_name='res.users', string='Requester', required=True,
        # readonly=True,
        default=lambda self: self.env.uid
    )
    product_request_line_ids = fields.One2many(comodel_name='vit.product.request.line',
        inverse_name='product_request_id',string='Product Lines',
        ondelete="cascade", copy= True,
        )

    product_request_lines = fields.Char(compute="_product_request_lines",
        string="Product Request Lines")

    department_id = fields.Many2one(comodel_name='hr.department', string='Department',default=_get_default_department_id,
        required=True,
        readonly=True,
        states={'draft':[('readonly',False)]})

    warehouse_id = fields.Many2one(comodel_name="stock.warehouse", string="Destination WH", 
        default=_get_default_warehouse_id,required=False, track_visibility='onchange', 
        readonly=True,
        states={'draft':[('readonly',False)]})

    category_id = fields.Many2one(comodel_name='product.category', string='Product Category',
        required=True,
        readonly=True,
        states={'draft':[('readonly',False)]},track_visibility='onchange'
        )
    notes = fields.Text(string="Request Notes",
        readonly=True,
        states={'draft':[('readonly',False)]},
        track_visibility='onchange'
        )
    state = fields.Selection(PR_STATES,'Status',readonly=True,required=True, default='draft',track_visibility='onchange')
    date_required   = fields.Date("Required Date",required=True,
                    readonly=True,
                    default=lambda *a : time.strftime("%Y-%m-%d"),
                    states={'draft':[('readonly',False)]}, track_visibility='onchange')
    partner_id = fields.Many2one("res.partner","Supplier", track_visibility='onchange',domain="[('supplier','=',True)]")
    payment_term_id = fields.Many2one("account.payment.term", "Payment Terms", related="partner_id.property_supplier_payment_term_id")
    reference = fields.Char("Reference", track_visibility='onchange')

    total = fields.Float(string="Total",  required=False, compute="_calc_total", store=True, track_visibility='onchange' )
    company_id = fields.Many2one(comodel_name='res.company', string='Company',required=True,readonly=True,states={'draft':[('readonly',False)]},
        default=lambda self: self.env.user.company_id, track_visibility='onchange')

    @api.onchange('department_id')
    def _onchange_department_id(self):
        if self.department_id:
            self.warehouse_id = self.department_id.warehouse_id
        else:
            self.warehouse_id = None

    @api.depends('product_request_line_ids','product_request_line_ids.subtotal' )
    def _calc_total(self):
        total = 0.0
        for rec in self:
            for line in rec.product_request_line_ids:
                total += line.subtotal
            rec.total = total

    @api.model
    def create(self,vals):
        dept = self.env['hr.department'].browse(int(vals['department_id']))
        vals['name'] = self.env['ir.sequence'].next_by_code('vit.product.request') + '/' + dept.name or '/'

        new_id = super(ProductRequest, self).create(vals)

        #add followers to managers
        partner_id=dept.manager_id.user_id.partner_id.id if dept.manager_id else False
        if partner_id:
            self.write({'message_follower_ids': [(4, partner_id)]})

        return new_id

    @api.multi
    def action_draft(self):
        #set to "draft" state
        body = _("PR set to draft")
        self.send_followers()

        self.update_line_state(PR_STATES[0][0])
        return self.write({'state':PR_STATES[0][0]})

    @api.multi
    def action_confirm(self):
        #set to "open" approved state
        body = _("PR confirmed")
        self.send_followers()
        self.update_line_state(PR_STATES[1][0])
        return self.write({'state':PR_STATES[1][0]})

    @api.multi
    def action_onprogress(self):
        #set to "onprogress" state
        body = _("PR on progress")
        self.send_followers()
        self.update_line_state(PR_STATES[2][0])
        return self.write({'state':PR_STATES[2][0]})

    @api.multi
    def action_done(self):
        #set to "done" state
        body = _("PR done")
        self.send_followers()
        self.update_line_state(PR_STATES[3][0])
        return self.write({'state':PR_STATES[3][0]})

    @api.multi
    def action_reject(self):
        #set to "reject" state
        body = _("PR reject")
        self.send_followers()
        self.update_line_state(PR_STATES[4][0])
        return self.write({'state':PR_STATES[4][0]})

    def update_line_state(self, state = None):
        for line in self.product_request_line_ids:
            line.write({'state':state}, )


    # create pr sekaligus dari product request
    def action_create_pr(self):
        cr = self.env.cr
        purchase_requisition          = self.env['purchase.requisition']
        purchase_requisition_line      = self.env['purchase.requisition.line']

        for prd_req in self:
            pr_line_ids = []
            for lines in prd_req.product_request_line_ids:
                pr_line_ids.append( (0,0,{
                    'product_id'    : lines.product_id.id,
                    'description'    : lines.name,
                    'product_qty'    : lines.product_qty,
                    'product_uom_id': lines.product_uom_id.id,
                    'schedule_date'    : lines.date_required,
                }) )
            partner = False
            if prd_req.partner_id:
                partner=self.partner_id.id
            pr_id = purchase_requisition.create({
                'name'            : self.env['ir.sequence'].get('purchase.requisition.purchase.tender'),
                'exclusive'        : 'exclusive',
                'warehouse_id'      : self.warehouse_id.id ,
                'line_ids'         : pr_line_ids,
                'partner_id'        : partner,
                'origin'          : prd_req.name
            })
            #update state dan pr_id di line product request asli
            cr.execute("update vit_product_request_line set state=%s, purchase_requisition_id=%s where product_request_id = %s",
             ( 'onprogress', pr_id.id,  prd_req.id  ))

            self.write({'state':'onprogress'}, )

            body = _("PR bid created")
            self.send_followers()

            return pr_id

    def send_followers(self=None):
        pass
        #records = self._get_followers()
        #followers = records[ids[0]]['message_follower_ids']
        #self.message_post(body=body,
        #                  subtype='mt_comment',
        #                  partner_ids=followers,
        #                  )

    @api.multi
    def add_follower(self, employee_id):
        employee = self.env['hr.employee'].browse(employee_id)
        if employee.user_id:
            #self.message_subscribe_users(user_ids=employee.user_id.ids)
            self.message_subscribe(partner_ids=[rec.responsible_id.partner_id.id], channel_ids=None, subtype_ids=None)

ProductRequest()


class ProductRequestLine(models.Model):
    _name         = "vit.product.request.line"
    _inherit        = ['mail.thread']


    product_request_id = fields.Many2one(comodel_name='vit.product.request', string='Product Request',ondelete='cascade')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    name = fields.Char("Description")
    product_qty = fields.Float('Quantity', default=1)

    product_qty_hand = fields.Float(
        related='product_id.qty_available',
        string="Quantity On Hand",
        store=False)

    product_qty_incoming = fields.Float(
        related='product_id.incoming_qty',
        string="Incoming Quantity",
        store=False)

    product_qty_outgoing = fields.Float(
        related='product_id.outgoing_qty' ,
        string="Outgoing Quantity",
        store=False)

    product_qty_avail = fields.Float(
         related='product_id.qty_available',
         string="Available Quantity",
         store=False)

    product_uom_id = fields.Many2one(
        comodel_name='uom.uom',
        string='Product UOM',
        store=True)

    product_qty_forecast = fields.Float(
         related='product_id.virtual_available',
         string="Forecast Quantity",
         store=False)


    unit_price = fields.Float(string="Price Unit",  required=True)
    subtotal = fields.Float(string="Subtotal",  required=False, compute="_calc_subtotal", store=True )

    department_id = fields.Many2one(comodel_name='hr.department', string='Department',
        readonly=True,
        related="product_request_id.department_id",
        store=True
        )

    warehouse_id = fields.Many2one(comodel_name='stock.warehouse', string='Warehouse',
        readonly=True,
        related="product_request_id.warehouse_id",
        store=True
        )

    date_required   = fields.Date("Required Date",required=True,
                    readonly=True,
                    default=lambda *a : time.strftime("%Y-%m-%d"),
                    states={'draft':[('readonly',False)]}, track_visibility='onchange')
    state = fields.Selection(PR_LINE_STATES,'Status',readonly=True,required=True, default='draft')
    purchase_requisition_id = fields.Many2one('purchase.requisition', 'Call for Bid',readonly=True)

    purchase_order_id = fields.Many2one(related='purchase_requisition_id.confirmed_po_id',
        comodel_name="purchase.order", string="RFQ/PO", store=True)


    @api.depends('unit_price','product_qty')
    def _calc_subtotal(self):
        for rec in self:
            rec.subtotal = rec.unit_price * rec.product_qty


    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
            self.unit_price = self.product_id.standard_price
            self.name = self.product_id.name
        else:
            self.product_uom_id = None
            self.unit_price = None

    def action_create_pr(self):
        state_not_open = self.filtered(lambda x: x.state != 'open')
        if state_not_open :
            raise UserError(_('Status product request line harus open (confirmed) !'))
        cr = self.env.cr
        ##########################################################
        # id line product_request_line yang diselect
        ##########################################################
        context=self.env.context
        active_ids = context and context.get('active_ids', False)

        ##########################################################
        # untuk setiap partner , create PO dari line PR
        ##########################################################
        prs = {}
        i=0
        sql = "select product_id, product_uom_id, department_id, warehouse_id, name, product_request_id, id, date_required, unit_price, " \
              "sum(product_qty) as product_qty " \
              "from vit_product_request_line " \
              "where state = 'open' and purchase_requisition_id is null " \
              "and id in %s " \
              "group by product_id, product_uom_id, department_id, warehouse_id, name, product_request_id, id, date_required " \
              "order by product_id, product_uom_id, department_id, warehouse_id, name, product_request_id, id, date_required "
        cr.execute(sql, ( tuple(active_ids),))
        res = cr.dictfetchall()

        for r in res:
            product_id = r['product_id']
            department_id = r['department_id']
            product_qty = r['product_qty']
            warehouse_id = r['warehouse_id']
            unit_price = r['unit_price']

            if product_id in prs:
                prs[product_id]['product_qty'] += product_qty
                prs[product_id]['origins'].append( r['product_request_id'])
                prs[product_id]['line_ids'].append( r['id'] )
                prs[product_id]['product_qty'] = unit_price
            else:
                prs[ product_id ] = {
                    'product_qty'    : product_qty ,
                    'product_uom_id' : r['product_uom_id'],
                    'schedule_date'  : r['date_required'] ,
                    'origins'        : [r['product_request_id']],
                    'line_ids'       : [r['id']],
                    'description'    : r['name'],
                    'price_unit'    : unit_price,
                }


            """
            qty_per_dept = { 
                dept_id1 : { qty: 10, request_id: 20, warehouse_id: 2} ,
                dept_id2 : { qty:  3, request_id: 21, warehouse_id: 3}
            }
            """
            if 'qty_per_dept' in prs[product_id]:
                if department_id in prs[product_id]['qty_per_dept']:
                    prs[product_id]['qty_per_dept'][department_id]['qty'] += product_qty
                    prs[product_id]['qty_per_dept'][department_id]['request_id'].append(r['product_request_id'])
                    prs[product_id]['qty_per_dept'][department_id]['warehouse_id'].append(r['warehouse_id'])
                else:
                    prs[product_id]['qty_per_dept'][department_id]= {'qty' : product_qty,
                                                                     'request_id': r['product_request_id'],
                                                                     'warehouse_id': r['warehouse_id']
                                                                     }

            else:
                prs[product_id]['qty_per_dept']= {department_id: {'qty':product_qty,
                                                                  'request_id': r['product_request_id'],
                                                                  'warehouse_id': r['warehouse_id']
                                                                  }}



        ##########################################################
        #create PR per produk diatas
        ##########################################################
        i = 0
        # import pdb; pdb.set_trace()
        for product_id in prs.keys():
            pr_id = self.create_pr(product_id, prs[product_id] )
            i = i + 1

        cr.commit()
        return {
            'type': 'ir.actions.act_window.message',
            'title': _('OK'),
            'message': 'Done creating %s Call for Bid(s) ' % (i),
            'close_button_title': 'Make this window go away',
            'is_html_message': True,
            'buttons': [
                # a button can be any action (also ir.actions.report.xml et al)
                {
                    'type': 'ir.actions.act_window',
                    'name': 'All customers',
                    'res_model': 'res.partner',
                    'view_mode': 'form',
                    'views': [[False, 'list'], [False, 'form']],
                    'domain': [('customer', '=', True)],
                },
                # or if type == method, you need to pass a model, a method name and
                # parameters
                {
                    'type': 'method',
                    'name': _('Yes, do it'),
                    'model': self._name,
                    'method': 'myfunction',
                    # list of arguments to pass positionally
                    'args': [self.ids],
                    # dictionary of keyword arguments
                    'kwargs': {'force': True},
                    # button style
                    'classes': 'btn-primary',
                }
            ]
        }



    def create_pr(self, product_id, request_line=None):
        cr=self.env.cr
        purchase_requisition  = self.env['purchase.requisition']
        product_request       = self.env['vit.product.request']
        origins = product_request.browse(request_line['origins'])

        line_department_ids = []
        for x in request_line['qty_per_dept'].keys():
            line_department_ids.append( (0,0,{
                'qty':request_line['qty_per_dept'][x]['qty'],
                'request_id':request_line['qty_per_dept'][x]['request_id'],
                'warehouse_id':request_line['qty_per_dept'][x]['warehouse_id'],
                'department_id': x}) )

        pr_line_ids = [(0,0,{
            'product_id': product_id,
            'product_qty': request_line['product_qty'],
            'price_unit' : request_line['price_unit'],
            'product_uom_id': request_line['product_uom_id'],
            'schedule_date': request_line['schedule_date'],
            'description': request_line['description'],
            'line_department_ids': line_department_ids
        })]
        pr_id = purchase_requisition.create({
            'name': self.env['ir.sequence'].get('purchase.requisition.purchase.tender'),
            'exclusive'    : 'exclusive',
            'warehouse_id'  : self.product_request_id.warehouse_id.id,
            'line_ids' : pr_line_ids,
            'origin'  : ",".join( [ x.name for x in origins ] )
        })


        #update state dan pr_id di line product request asli
        cr.execute("update vit_product_request_line set state=%s, purchase_requisition_id=%s where id in %s",
         ( 'onprogress', pr_id.id, tuple(request_line['line_ids'])))

        return pr_id

    @api.model
    def create(self, vals):
        vals['department_id']    = self.env["vit.product.request"].browse(int(vals['product_request_id'])).department_id.id
        return super(ProductRequestLine, self).create(vals)

ProductRequestLine()


class PurchaseRequisition(models.Model):
    _name = 'purchase.requisition'
    _inherit = 'purchase.requisition'

    def unlink(self=None):
        cr = self.env.cr
        cr.execute("update vit_product_request_line set state=%s where purchase_requisition_id in %s ", ('open', tuple(self._ids))  )
        return super(PurchaseRequisition, self).unlink()

    def tender_done(self=None):
        cr = self.env.cr
        cr.execute("update vit_product_request_line set state=%s where purchase_requisition_id in %s ", ('done', tuple(self._ids))  )
        return super(PurchaseRequisition, self).tender_done()

PurchaseRequisition()


class PurchaseRequisitionLine(models.Model):
    _name = 'purchase.requisition.line'
    _inherit = 'purchase.requisition.line'

    def unlink(self=None):
        cr = self.env.cr
        cr.execute("update vit_product_request_line set state=%s, purchase_requisition_id=null where product_id = %s and purchase_requisition_id in %s ", ('open', self.product_id.id,tuple(self.requisition_id._ids))  )
        return super(PurchaseRequisitionLine, self).unlink()

PurchaseRequisitionLine()
