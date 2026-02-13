from odoo import fields, models


class BookingResourceCategory(models.Model):
    """
    Category for booking resources.
    Holds the properties definition that can be shared across resources.
    """
    _name = 'booking.resource.category'
    _description = 'Booking Resource Category'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
    )

    # Related resources
    resource_ids = fields.One2many(
        'booking.resource.type',
        'category_id',
        string='Resources',
    )
    resource_count = fields.Integer(
        string='Resource Count',
        compute='_compute_resource_count',
    )

    def _compute_resource_count(self):
        for category in self:
            category.resource_count = len(category.resource_ids)
