# -*- coding: utf-8 -*-
from odoo import models, fields


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
    task_ids = fields.One2many('su.task', 'brigade_id', string='Задачи')
    active = fields.Boolean(default=True)
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        default=lambda self: self.env.company,
        required=True,
    )
