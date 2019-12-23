#!/usr/bin/python
#-*- coding: utf-8 -*-

from odoo import models, fields, api, _

class justifikasi(models.Model):
    _name = "vit.justifikasi"
    _inherit = "vit.justifikasi"
    def Operation1(self, ):
        pass

    pr_date = fields.Date( string="PR date",  help="", related="pr_id.date", readonly=True)

    @api.model
    def create(self, vals):
        vals['name']    = self.env['ir.sequence'].next_by_code('vit.justifikasi')
        return super(justifikasi, self).create(vals)
