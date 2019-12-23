from odoo import tools
from odoo import fields,models
import time
import logging
from odoo.tools.translate import _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class purchase_requisition_line(models.Model):
    _name     = "purchase.requisition.line"
    _inherit     = "purchase.requisition.line"

    def onchange_product_id(self, ids, product_id, product_uom_id, parent_analytic_account, analytic_account, parent_date, date, context=None):
        """ Changes UoM and name if product_id changes.
        @param name: Name of the field
        @param product_id: Changed product_id
        @return:  Dictionary of changed values
        """
        value = {'product_uom_id': ''}
        if product_id: 
            prod = self.pool.get('product.product').browse(product_id, context=context)
            value = {'product_uom_id': prod.uom_id.id}
        if not analytic_account:
            value.update({'account_analytic_id': parent_analytic_account})
        if not date:
            value.update({'schedule_date': parent_date})
        return {'value': value}

    description = fields.Char('Description')

    line_department_ids = fields.One2many(comodel_name="vit.pr_line_department",
                                          inverse_name="pr_line_id", string="Line per Department",
                                          required=False, )



class pr_line_department(models.Model):

    _name = "vit.pr_line_department"
    
    pr_line_id = fields.Many2one(comodel_name="purchase.requisition.line", string="PR Line", required=False, )
    qty = fields.Float(string="Quantity",  required=False, )
    department_id = fields.Many2one(comodel_name="hr.department", string="Department", required=False, )
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse", string="Warehouse", required=False, )
    request_id = fields.Many2one(comodel_name="vit.product.request", string="Origin", required=False, )



class purchase_requisition(models.Model):
    _name     = "purchase.requisition"
    _inherit     = "purchase.requisition"

    def _product_names(self):
        results = {}
        # return harus berupa dictionary dengan key id session
        # contoh kalau 3 records:
        # {
        #      1 : 50.8,
        #      2 : 25.5,
        #      3 : 10.0
        # }

        for pr in self:
            product_names = []
            for line in pr.line_ids:
                product_names.append( "%s/%s" % (line.product_id.name , line.description) )
                results[pr.id] = ",".join(product_names)
        return results

    def tender_in_progress(self, ids, context=None):
        header=[]
        for line in self.line_ids:
            if line.product_id.is_header and line.product_id.categ_id.display_name.find('Non Starting Material')==-1:
                # since inly 1 id, and return value is [(id,name)]
                header.append(line.product_id.name_get()[0][1])
        if header:
            raise UserError(_('Warning!'), _('Produk berikut harus diganti menjadi produk dengan serial no 10 digit \n%s.') % '\n'.join(header))
        self.write({'approved_date': time.strftime('%Y-%m-%d')})
        return super(purchase_requisition,self).tender_in_progress( ids, context=None)

    def _get_confirmed_po(self):
        for pr in self:
            for po in pr.purchase_ids:
                if po.state in ('done','purchase'):
                    pr.confirmed_po_id = po.id

    product_names = fields.Char(compute="_product_names", string="Products")
    approved_date = fields.Date(string="approved date" , readonly=True, default=lambda self: time.strftime('%Y-%m-%d'))
    confirmed_po_id = fields.Many2one(
        comodel_name="purchase.order",
        compute=_get_confirmed_po,
        string='Confirmed PO',
        store=False,
        help = 'Confirmed PO')
    department_id = fields.Many2one(comodel_name='hr.department',string='Department')

    

    def _prepare_purchase_order(self, requisition, supplier):
        department_id = False
        res = super(purchase_requisition, self)._prepare_purchase_order(requisition, supplier)
        b = self.env['vit.new.product.request'].search([('name','=', requisition.origin)])
        pr = self.env['vit.new.product.request'].browse(b)
        department_id = pr[0].department_id.id
        res.update({'department_id': department_id})
        return res