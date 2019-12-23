from odoo import api, fields, models, _
from odoo.tools.float_utils import float_is_zero, float_compare
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class po_line(models.Model):
    _name = 'purchase.order.line'
    _inherit = 'purchase.order.line'
        

    line_department_ids = fields.One2many(comodel_name="vit.po_line_department",
                                          inverse_name="po_line_id", string="Line per Department",
                                          required=False, )


    @api.multi
    def _my_prepare_stock_moves(self, picking, qty, warehouse_id):
        """ Prepare the stock moves data for one order line. This function returns a list of
        dictionary ready to be used in stock.move's create()
        """
        self.ensure_one()
        res = []
        if self.product_id.type not in ['product', 'consu']:
            return res

        price_unit = self._get_stock_move_price_unit()

        template = {
            'name': self.name or '',
            'product_id': self.product_id.id,
            'product_uom': self.product_uom.id,
            'date': self.order_id.date_order,
            'date_expected': self.date_planned,
            'location_id': self.order_id.partner_id.property_stock_supplier.id,
            'location_dest_id': warehouse_id.lot_stock_id.id,
            'picking_id': picking.id,
            'partner_id': self.order_id.dest_address_id.id,
            'move_dest_id': False,
            'state': 'draft',
            'purchase_line_id': self.id,
            'company_id': self.order_id.company_id.id,
            'price_unit': price_unit,
            'picking_type_id': picking.picking_type_id.id,
            'group_id': self.order_id.group_id.id,
            'procurement_id': False,
            'origin': self.order_id.name,
            'route_ids': warehouse_id and [(6, 0, [x.id for x in warehouse_id.route_ids])] or [],
            'warehouse_id': warehouse_id.id,
            'product_uom_qty': qty,
        }

        res.append(template)
        return res

    @api.multi
    def _my_create_stock_moves(self, picking, qty, warehouse_id):
        moves = self.env['stock.move']
        done = self.env['stock.move'].browse()
        for line in self:
            for val in line._my_prepare_stock_moves(picking, qty, warehouse_id):
                done += moves.create(val)
        return done

class po_line_department(models.Model):

    _name = "vit.po_line_department"
    
    po_line_id = fields.Many2one(comodel_name="purchase.order.line", string="PO Line", required=False, )
    qty = fields.Float(string="Quantity",  required=False, )
    department_id = fields.Many2one(comodel_name="hr.department", string="Department", required=False, )
    warehouse_id = fields.Many2one(comodel_name="stock.warehouse", string="Warehouse", required=False, )
    request_id = fields.Many2one(comodel_name="vit.product.request", string="Request", required=False, )



class po(models.Model):
    _name = 'purchase.order'
    _inherit = 'purchase.order'

    @api.model
    def create(self, vals):
        res = super(po, self).create(vals)
        if res.requisition_id:
            for pr_line in res.requisition_id.line_ids:
                for line in res.order_line:
                    if pr_line.product_id == line.product_id:
                       line.line_department_ids=[(0,0,{'department_id': x.department_id,
                                                       'request_id': x.request_id,
                                                       'warehouse_id': x.warehouse_id,
                                                       'qty': x.qty}) for x in pr_line.line_department_ids]

            t_qty = sum(res.requisition_id.line_ids.mapped('product_qty'))
            t_amount = sum(res.requisition_id.line_ids.mapped('price_unit'))

            # hanya protek harga ketika sudah PO
            if 'state' in vals and vals['state'] != 'draft':
                if res.amount_total > (t_qty*t_amount):
                    raise UserError(_('Max revisi total PO Rp. %s  \n Total nilai PO saat ini Rp. %s') % (str(t_qty*t_amount),str(res.amount_total)))
        return res

    @api.multi
    def write(self, vals):
        _super = super(po, self).write(vals)
        if self.requisition_id :
            t_qty = sum(self.requisition_id.line_ids.mapped('product_qty'))
            t_amount = sum(self.requisition_id.line_ids.mapped('price_unit'))

            if self.state not in ['draft','cancel']:
                if self.amount_total > (t_qty*t_amount):
                    raise UserError(_('Max revisi total PO (Bidding) Rp. %s  \n Total nilai PO saat ini Rp. %s') % (str(t_qty*t_amount),str(self.amount_total)))
        return _super

    # komen dulu karena ketika create dokumen receive jd double sesuai line PO
    # @api.multi
    # def _create_picking(self):
    #     if not self.requisition_id:
    #         res = super(po, self)._create_picking()
    #         return res

    #     else:
    #         # create pickings based on line.line_department_ids for each departments
    #         res = self._my_create_picking()
    #         return res

    def _my_create_picking(self):

        """
        po_line_id
        qty
        department_id
        request_id
        :return:
        """
        StockPicking = self.env['stock.picking']
        for order in self:
            if any([ptype in ['product', 'consu'] for ptype in order.order_line.mapped('product_id.type')]):
                for line in order.order_line:
                    for qty_per_dept in line.line_department_ids:
                        qty = qty_per_dept.qty
                        department_id = qty_per_dept.department_id
                        request_id = qty_per_dept.request_id
                        warehouse_id = qty_per_dept.warehouse_id
                        picking_type_id = warehouse_id.in_type_id

                        res = order._prepare_picking()
                        res['department_id']=department_id.id
                        res['request_id']=request_id.id
                        res['picking_type_id']=picking_type_id.id
                        res['location_dest_id']=picking_type_id.default_location_dest_id.id
                        picking = StockPicking.create(res)

                        moves = order.order_line._my_create_stock_moves(picking, qty, warehouse_id)
                        moves = moves.filtered(lambda x: x.state not in ('done', 'cancel')).action_confirm()

                        seq = 0
                        for move in sorted(moves, key=lambda move: move.date_expected):
                            seq += 5
                            move.sequence = seq

                        moves.force_assign()

                        picking.message_post_with_view('mail.message_origin_link',
                            values={'self': picking, 'origin': order},
                            subtype_id=self.env.ref('mail.mt_note').id)
        return True