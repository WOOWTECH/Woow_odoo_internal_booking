from odoo import fields, models


class BookingResourceCategory(models.Model):
    """
    Tag / category for booking resources.
    Uses the standard Odoo tag pattern (name + color) with Many2many.
    """
    _name = 'booking.resource.category'
    _description = 'Booking Resource Category'
    _order = 'name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    color = fields.Integer(
        string='Color',
    )
