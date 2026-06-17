from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from datetime import datetime, timedelta


class BookingResourceType(models.Model):
    _name = 'booking.resource.type'
    _description = 'Booking Resource'
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    # Basic information
    name = fields.Char(
        string='Name',
        required=True,
        translate=True,
        tracking=True,
    )
    description = fields.Html(
        string='Description',
        translate=True,
    )
    image = fields.Image(
        string='Image',
        max_width=512,
        max_height=512,
    )
    sequence = fields.Integer(
        string='Sequence',
        default=10,
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        tracking=True,
    )

    # WELL Building Standard space classification
    well_space_type = fields.Selection([
        ('V08', 'V08 - Physical Activity Space'),
        ('M04', 'M04 - Mindfulness Space'),
        ('M06', 'M06 - Community Space'),
        ('C01', 'C01 - Family Support Space'),
        ('none', 'General Space'),
    ], string='WELL Space Type', default='none',
        help='WELL Building Standard space type classification')

    # Resource details
    location = fields.Char(
        string='Location',
        translate=True,
    )
    capacity = fields.Integer(
        string='Capacity',
        default=1,
        help='Maximum capacity of the resource',
    )

    # Slot settings
    slot_duration = fields.Float(
        string='Slot Duration (Hours)',
        default=1.0,
        required=True,
        help='Duration of each booking slot in hours',
    )
    slot_interval = fields.Float(
        string='Slot Interval (Hours)',
        default=1.0,
        help='Interval between available slots. Set equal to slot duration to avoid overlap.',
    )
    advance_days = fields.Integer(
        string='Advance Booking Days',
        default=30,
        help='How many days in advance users can book this resource',
    )

    # Availability (weekly recurring schedule)
    availability_ids = fields.One2many(
        'booking.resource.availability',
        'resource_type_id',
        string='Availability',
        help='Define weekly recurring availability time slots',
    )

    # Discussion settings
    enable_discussion = fields.Boolean(
        string='Allow Discussion Channel',
        default=False,
        help='When enabled, users booking this resource can create a discussion channel for the reservation.',
    )

    # Access control
    share_type = fields.Selection(
        selection=[
            ('all', 'All Portal Users'),
            ('specific', 'Specific Contacts'),
        ],
        string='Access Type',
        default='specific',
        required=True,
        tracking=True,
        help='Control who can book this resource',
    )
    allowed_partner_ids = fields.Many2many(
        'res.partner',
        'booking_resource_type_partner_rel',
        'resource_type_id',
        'partner_id',
        string='Allowed Contacts',
        domain="[('is_company', '=', False)]",
        help='Select contacts allowed to book this resource (Portal users). Only applies when access type is "Specific Contacts".',
    )

    # Categories (tag-style, Many2many)
    category_ids = fields.Many2many(
        'booking.resource.category',
        'booking_resource_type_category_rel',
        'resource_type_id',
        'category_id',
        string='Categories',
    )

    # Dynamic properties definition (Odoo 18 native)
    # Defines what properties are available for reservations of this resource.
    # Actual property values are stored on booking.reservation via resource_properties field.
    resource_properties_definition = fields.PropertiesDefinition(
        string='Properties Definition',
    )

    # Related reservations
    reservation_ids = fields.One2many(
        'booking.reservation',
        'resource_type_id',
        string='Reservations',
    )
    reservation_count = fields.Integer(
        string='Reservation Count',
        compute='_compute_reservation_count',
    )

    @api.depends('reservation_ids')
    def _compute_reservation_count(self):
        if not self.ids:
            self.reservation_count = 0
            return
        counts = {}
        for row in self.env['booking.reservation']._read_group(
            domain=[('resource_type_id', 'in', self.ids), ('state', '=', 'confirmed')],
            groupby=['resource_type_id'],
            aggregates=['__count'],
        ):
            counts[row[0].id] = row[1]
        for record in self:
            record.reservation_count = counts.get(record.id, 0)

    @api.constrains('slot_duration', 'slot_interval')
    def _check_slot_settings(self):
        for record in self:
            if record.slot_duration <= 0:
                raise ValidationError(_('Slot duration must be a positive number.'))
            if record.slot_interval <= 0:
                raise ValidationError(_('Slot interval must be a positive number.'))
            if record.slot_interval < 0.25:
                raise ValidationError(_('Slot interval cannot be less than 15 minutes (0.25 hours).'))

    @api.constrains('capacity')
    def _check_capacity(self):
        for record in self:
            if record.capacity < 1:
                raise ValidationError(_('Capacity must be at least 1.'))

    @api.constrains('advance_days')
    def _check_advance_days(self):
        for record in self:
            if record.advance_days < 1:
                raise ValidationError(_('Advance booking days must be at least 1 day.'))

    def _check_partner_access(self, partner):
        """Check if a partner has access to book this resource."""
        self.ensure_one()
        if self.share_type == 'all':
            return True
        return partner.id in self.allowed_partner_ids.ids

    def _generate_slots(self, date_from, date_to):
        """
        Generate available time slots for this resource.

        Args:
            date_from: Start date
            date_to: End date

        Returns:
            List of slot dictionaries with start/end datetime and availability
        """
        self.ensure_one()
        slots = []
        current_date = date_from

        while current_date <= date_to:
            day_of_week = str(current_date.weekday())
            availabilities = self.availability_ids.filtered(
                lambda a: a.dayofweek == day_of_week
            )

            for availability in availabilities:
                current_hour = availability.hour_from

                while current_hour + self.slot_duration <= availability.hour_to:
                    # Create datetime for slot start
                    hour = int(current_hour)
                    minute = int((current_hour % 1) * 60)
                    start_dt = datetime.combine(
                        current_date,
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                    end_dt = start_dt + timedelta(hours=self.slot_duration)

                    slots.append({
                        'start': start_dt,
                        'end': end_dt,
                        'start_str': start_dt.strftime('%Y-%m-%d %H:%M'),
                        'end_str': end_dt.strftime('%H:%M'),
                        'date_str': start_dt.strftime('%Y-%m-%d'),
                    })

                    current_hour += self.slot_interval

            current_date += timedelta(days=1)

        return slots

    def action_view_reservations(self):
        """Open reservations for this resource."""
        self.ensure_one()
        return {
            'name': _('Reservations'),
            'type': 'ir.actions.act_window',
            'res_model': 'booking.reservation',
            'view_mode': 'calendar,tree,form',
            'domain': [('resource_type_id', '=', self.id)],
            'context': {'default_resource_type_id': self.id},
        }
