# -*- coding: utf-8 -*-
from odoo import models, fields, api


class SuBrigade(models.Model):
    _name = 'su.brigade'
    _description = 'Бригада'
    _order = 'name'

    name = fields.Char(string='Название', required=True)
    foreman_id = fields.Many2one(
        'res.users',
        string='Бригадир',
    )
    specialty = fields.Selection([
        ('general', 'Общестроительные'),
        ('electrical', 'Электромонтажные'),
        ('plumbing', 'Сантехнические'),
        ('finishing', 'Отделочные'),
        ('roofing', 'Кровельные'),
        ('foundation', 'Фундаментные'),
        ('other', 'Прочие'),
    ], string='Специализация')
    member_ids = fields.Many2many(
        'res.users',
        'su_brigade_member_rel',
        'brigade_id',
        'user_id',
        string='Члены бригады',
    )
    member_count = fields.Integer(
        string='Членов',
        compute='_compute_member_count',
        store=True,
    )
    task_ids = fields.One2many('su.task', 'brigade_id', string='Задачи')
    active_task_count = fields.Integer(
        string='Активных задач',
        compute='_compute_active_task_count',
    )
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        default=lambda self: self.env.company,
        required=True,
    )

    @api.depends('member_ids')
    def _compute_member_count(self):
        for brigade in self:
            brigade.member_count = len(brigade.member_ids)

    def _compute_active_task_count(self):
        for brigade in self:
            brigade.active_task_count = self.env['su.task'].search_count([
                ('brigade_id', '=', brigade.id),
                ('state', 'in', ('new', 'in_progress', 'review')),
            ])

    def action_view_tasks(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Задачи бригады',
            'res_model': 'su.task',
            'view_mode': 'kanban,tree,form',
            'domain': [('brigade_id', '=', self.id)],
            'context': {'default_brigade_id': self.id},
        }
