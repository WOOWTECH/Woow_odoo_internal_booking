from odoo import fields, models


class BookingResourceCategory(models.Model):
    """
    Category for booking resources.
    Holds the properties definition that can be shared across resources.
    """
    _name = 'booking.resource.category'
    _description = 'Booking Resource Category'
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

    # Properties definition for this category
    resource_properties_definition = fields.PropertiesDefinition(
        string='Resource Properties',
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
        if not self.ids:
            self.resource_count = 0
            return
        counts = {}
        for row in self.env['booking.resource.type']._read_group(
            domain=[('category_id', 'in', self.ids)],
            groupby=['category_id'],
            aggregates=['__count'],
        ):
            counts[row[0].id] = row[1]
        for category in self:
            category.resource_count = counts.get(category.id, 0)
