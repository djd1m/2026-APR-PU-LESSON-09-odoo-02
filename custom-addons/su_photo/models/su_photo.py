# -*- coding: utf-8 -*-
from odoo import models, fields


class SuPhoto(models.Model):
    _name = 'su.photo'
    _description = 'Фотофиксация'
    _order = 'taken_at desc, id desc'

    name = fields.Char(string='Название', compute='_compute_name', store=True)
    project_id = fields.Many2one(
        'su.project',
        string='Объект',
        ondelete='cascade',
        required=True,
    )
    task_id = fields.Many2one(
        'su.task',
        string='Задача',
        domain="[('project_id', '=', project_id)]",
    )
    image = fields.Binary(
        string='Фото',
        required=True,
        attachment=True,
    )
    image_filename = fields.Char(string='Имя файла')
    description = fields.Text(string='Описание')
    latitude = fields.Float(string='Широта', digits=(10, 7))
    longitude = fields.Float(string='Долгота', digits=(10, 7))
    taken_at = fields.Datetime(
        string='Дата съёмки',
        default=fields.Datetime.now,
    )
    author_id = fields.Many2one(
        'res.users',
        string='Автор',
        default=lambda self: self.env.user,
    )
    company_id = fields.Many2one(
        'res.company',
        string='Компания',
        related='project_id.company_id',
        store=True,
    )

    def _compute_name(self):
        for photo in self:
            parts = []
            if photo.project_id:
                parts.append(photo.project_id.name or '')
            if photo.task_id:
                parts.append(photo.task_id.name or '')
            if photo.taken_at:
                parts.append(fields.Datetime.to_string(photo.taken_at)[:10])
            photo.name = ' / '.join(parts) if parts else 'Фото'
