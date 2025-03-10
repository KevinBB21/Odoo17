# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class UsuarioBiblioteca(models.Model):
    _name = 'usuario.biblioteca'
    _description = 'Usuario Biblioteca'
    _order = 'nombre'
    _rec_name = 'nombre'

    nombre = fields.Char('Nombre', required=True)
    telefono = fields.Char('Teléfono')
    apellido = fields.Char('Apellido')
    ejemplar_ids = fields.One2many('ejemplar.biblioteca', 'usuario_id', string='Ejemplares en Préstamo')

    @api.depends('ejemplar_ids')
    def _compute_ejemplares_disponibles(self):
        ejemplares_disponibles = self.env['ejemplar.biblioteca'].search([('esta_disponible', '=', True)])
        for usuario in self:
            usuario.ejemplar_disponibles_ids = ejemplares_disponibles

    ejemplar_disponibles_ids = fields.One2many(
        comodel_name='ejemplar.biblioteca',
        compute='_compute_ejemplares_disponibles',
        string="Ejemplares Disponibles"
    )
