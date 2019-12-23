# -*- coding: utf-8 -*-
from odoo import models, api, _
from odoo.exceptions import UserError


class ProductRequestLineWizard(models.TransientModel):

    _name = "vit.product.request.line.wizard"
    _description = "Confirm the selected invoices"

    @api.multi
    def create_agreements(self):
        context = dict(self._context or {})
        active_ids = context.get('active_ids', []) or []

        for record in self.env['vit.product.request.line'].browse(active_ids):
            if record.state != 'open':
                raise UserError(_("Selected PR lines cannot be confirmed as they are not in 'Open' state."))
            record.action_create_pr()
        return {'type': 'ir.actions.act_window_close'}

ProductRequestLineWizard()