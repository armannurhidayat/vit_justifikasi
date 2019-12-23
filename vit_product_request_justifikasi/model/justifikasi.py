#!/usr/bin/python
#-*- coding: utf-8 -*-

from odoo import models, fields, api, _

class justifikasi(models.Model):
	_name = "vit.justifikasi"

	name = fields.Char( required=True, string="Name", default="/", readonly=True,  help="")
	date = fields.Date( string="Tanggal",  help="")
	no_sop = fields.Char( string="No SOP",  help="")
	revisi_ke = fields.Integer( string="Revisi ke",  help="")
	no_urut_proses = fields.Integer( string="No urut proses",  help="")
	kebutuhan = fields.Selection(selection=[('operasional','Operasional Kantor') , ('bisnis', 'Bisnis')],  string="Kebutuhan",  help="")
	pr_date = fields.Date( string="PR date",  help="")
	nama_kegiatan = fields.Char( string="Nama kegiatan",  help="")
	job_list = fields.Char( string="Job list",  help="")
	referensi_dokumen_penunjang = fields.Char( string="Referensi dokumen penunjang",  help="")
	alasan_pertimbangan = fields.Text( string="Alasan pertimbangan",  help="")
	spesifikasi_kebutuhan = fields.Text( string="Spesifikasi kebutuhan",  help="")
	jumlah_kebutuhan = fields.Float( string="Jumlah kebutuhan",  help="")
	budget_tersedia = fields.Float( string="Budget tersedia",  help="")
	estimasi_kebutuhan_budget = fields.Float( string="Estimasi kebutuhan budget",  help="")
	waktu_penggunaan = fields.Date( string="Waktu penggunaan",  help="")
	distribusi_penggunaan = fields.Char( string="Distribusi penggunaan",  help="")
	posisi_persediaan = fields.Char( string="Posisi persediaan",  help="")
	diajukan_tanggal = fields.Date( string="Diajukan tanggal",  help="")
	diketahui_tanggal = fields.Date( string="Diketahui tanggal",  help="")
	disetujui_tanggal = fields.Date( string="Disetujui tanggal",  help="")


	pr_id = fields.Many2one(comodel_name="vit.product.request",  string="PR",  help="")
	responsible_id = fields.Many2one(comodel_name="hr.employee",  string="Responsible",  help="")
	coa_id = fields.Many2one(comodel_name="account.account",  string="Coa",  help="")
	diajukan_oleh = fields.Many2one(comodel_name="res.users",  string="Diajukan oleh",  help="")
	diketahui_oleh = fields.Many2one(comodel_name="res.users",  string="Diketahui oleh",  help="")
	disetujui_oleh = fields.Many2one(comodel_name="res.users",  string="Disetujui oleh",  help="")
	company_id = fields.Many2one(comodel_name="res.company",  string="Company",  help="")






	@api.multi
	def create_purchase_requisition(self):
		action = self.env.ref('vit_product_request.action_product_request')
		result = action.read()[0]
		create_purchase_requisition = self.env.context.get('create_purchase_requisition', False)
		
		print(create_purchase_requisition)
		result['context'] = {
			'default_referece_name': self.name,
		}

		if len(self.pr_id) > 1 and not create_purchase_requisition:
			result['domain'] = "[('id', 'in', " + str(self.pr_id.id) + ")]"
		else:
			res = self.env.ref('vit_product_request.view_product_request_form', False)
			
			form_view = [(res and res.id or False, 'form')]
			if 'views' in result:
				result['views'] = form_view + [(state,view) for state,view in action['views'] if view != 'form']
			else:
				result['views'] = form_view
			if not create_purchase_requisition:
				result['res_id'] = self.pr_id.id or False
		result['context']['default_reference'] = self.name
		return result