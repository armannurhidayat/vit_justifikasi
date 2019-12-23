#!/usr/bin/python
#-*- coding: utf-8 -*-

from odoo import models, fields, api, _

class product_request(models.Model):
    _name = "vit.product.request"
    _inherit = "vit.product.request"


    justifikasi_ids = fields.One2many(comodel_name="vit.justifikasi",  inverse_name="pr_id",  string="PRs",  help="")
    justifikasi_count = fields.Integer("Justifiasi(s)", compute="_get_justifikasi_count")

    def _get_justifikasi_count(self):
        for rec in self:
            rec.justifikasi_count = len(rec.justifikasi_ids)

    @api.multi
    def action_view_justifikasi(self):
        action = self.env.ref('vit_product_request_justifikasi.action_vit_justifikasi')
        result = action.read()[0]

        result['context'] = {
            'default_pr_id': self.id,
            'default_company_id': self.company_id.id,
            'company_id': self.company_id.id
        }
        # choose the view_mode accordingly
        if len(self.justifikasi_ids) > 1 :
            result['domain'] = "[('id', 'in', " + str(self.justifikasi_ids.ids) + ")]"
        else:
            res = self.env.ref('view_vit_justifikasi_form', False)
            result['views'] = [(res and res.id or False, 'form')]
            result['res_id'] = self.justifikasi_ids.id or False
        return result