# -*- coding: utf-8 -*-
from datetime import timedelta, date
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class EjemplarBiblioteca(models.Model):
    _name = 'ejemplar.biblioteca'
    _description = 'Ejemplar para Préstamo'
    _rec_name = 'display_name'

    comic_id = fields.Many2one('biblioteca.comic', string='Cómic')
    usuario_id = fields.Many2one('usuario.biblioteca', string='Usuario en Préstamo', ondelete='set null')
    fecha_prestamo = fields.Date('Fecha de Préstamo', default=fields.Date.today)
    fecha_devolucion = fields.Date('Fecha Esperada de Devolución')
    retrasado = fields.Boolean('Entrega Retrasada', compute='_compute_retraso', store=True)
    disponibilidad = fields.Char('Disponible', compute='_compute_disponible', default="Disponible", store=True)
    esta_disponible = fields.Boolean(string="¿Disponible?", compute="_compute_esta_disponible", store=True)
    portada = fields.Binary(string="Portada Relacionada", related='comic_id.portada', store=False, readonly=True)
    estado_de_conservacion = fields.Selection([
        ('perfecto', 'Perfecto'),
        ('regular', 'Regular'),
        ('danado', 'Dañado'),
        ('roto', 'Roto')
    ], string='Estado de Conservación', default='perfecto')
    display_name = fields.Char(string='Ejemplar', compute='_compute_display_name', store=True)

    _sql_constraints = [
        ('fecha_prestamo_check', 'CHECK(fecha_prestamo <= CURRENT_DATE)', 'La fecha de préstamo no puede ser posterior al día de hoy.'),
        ('fecha_devolucion_check', 'CHECK(fecha_devolucion >= CURRENT_DATE)', 'La fecha prevista de devolución no puede ser anterior al día de hoy.'),
        ('check_fechas', 'CHECK(fecha_prestamo < fecha_devolucion)', 'La fecha de devolución debe ser posterior a la fecha de préstamo.')
    ]

    @api.depends('fecha_devolucion')
    def _compute_retraso(self):
        hoy = fields.Date.today()
        for record in self:
            record.retrasado = record.fecha_devolucion and record.fecha_devolucion < hoy

    @api.depends('usuario_id')
    def _compute_esta_disponible(self):
        for record in self:
            record.esta_disponible = not bool(record.usuario_id)

    @api.onchange('usuario_id')
    def _delete_if_no_user(self):
        for record in self:
            if not record.usuario_id:
                record.esta_disponible = True
                record.fecha_devolucion = False
                record.fecha_prestamo = False
                record.disponibilidad = "Disponible"

    @api.depends('usuario_id', 'retrasado', 'fecha_devolucion')
    def _compute_disponible(self):
        for record in self:
            record.disponibilidad = "Disponible" if not record.usuario_id else "Devolución retrasada" if record.retrasado else str(record.fecha_devolucion)

    @api.depends('comic_id', 'estado_de_conservacion')
    def _compute_display_name(self):
        for record in self:
            if record.comic_id:
                estado = dict(self._fields['estado_de_conservacion'].selection).get(record.estado_de_conservacion)
                record.display_name = f"{record.comic_id.nombre} ({estado})"
            else:
                record.display_name = "Sin cómic asociado"

    @api.model
    def obtener_ejemplares_disponibles(self):
        return self.search([('esta_disponible', '=', True)])

    def action_prestar_individual(self):
        usuario_id = self.env.context.get('usuario_biblioteca_id')
        ejemplar_id = self.env.context.get('ejemplar_id')
        if not usuario_id or not ejemplar_id:
            raise ValidationError("Ha ocurrido un error. No se pudo determinar el usuario o el ejemplar.")
        usuario = self.env['usuario.biblioteca'].browse(usuario_id)
        ejemplar = self.env['ejemplar.biblioteca'].browse(ejemplar_id)
        if not usuario.exists() or not ejemplar.exists():
            raise ValidationError(f"No se encontró el Usuario {usuario_id} o el Ejemplar {ejemplar_id} en el sistema.")
        if not ejemplar.esta_disponible:
            raise ValidationError(f"El ejemplar '{ejemplar.display_name}' no está disponible.")
        ejemplar.write({
            'usuario_id': usuario.id,
            'esta_disponible': False,
            'fecha_prestamo': fields.Date.context_today(self),
            'fecha_devolucion': fields.Date.context_today(self) + timedelta(days=15),
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_devolver_individual(self):
        for record in self:
            if record.esta_disponible:
                raise ValidationError("El ejemplar ya está disponible. No se puede devolver.")
            record.esta_disponible = True
            record.usuario_id = False
            record.fecha_devolucion = fields.Date.context_today(self)
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': 'Devolución Exitosa',
                'message': f'El ejemplar "{record.display_name}" ha sido devuelto.',
                'type': 'success',
                'sticky': False,
                'next': {
                    'type': 'ir.actions.client',
                    'tag': 'reload',
                },
            },
        }
