from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from datetime import datetime, timedelta


class BookingResourceType(models.Model):
    _name = 'booking.resource.type'
    _description = 'Booking Resource Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'sequence, name'

    # Basic Information
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

    # Resource Details
    location = fields.Char(
        string='Location',
        translate=True,
    )
    capacity = fields.Integer(
        string='Capacity',
        default=1,
        help='Maximum capacity of the resource',
    )

    # Slot Settings
    slot_duration = fields.Float(
        string='Slot Duration (hours)',
        default=1.0,
        required=True,
        help='Duration of each booking slot in hours',
    )
    slot_interval = fields.Float(
        string='Slot Interval (hours)',
        default=1.0,
        help='Time interval between available slots. Set same as duration for non-overlapping slots.',
    )
    advance_days = fields.Integer(
        string='Days Available in Advance',
        default=30,
        help='How many days in advance can users book this resource',
    )

    # Availability (recurring weekly schedule)
    availability_ids = fields.One2many(
        'booking.resource.availability',
        'resource_type_id',
        string='Available Hours',
        help='Define recurring availability windows for each day of the week',
    )

    # Access Control
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
        help='Select contacts (Portal users) who can book this resource. Only applies when Access Type is "Specific Contacts".',
    )

    # Category (optional grouping)
    category_id = fields.Many2one(
        'booking.resource.category',
        string='Category',
        ondelete='set null',
        index=True,
    )

    # Related Reservations
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
        for record in self:
            record.reservation_count = len(record.reservation_ids.filtered(
                lambda r: r.state == 'confirmed'
            ))

    @api.constrains('slot_duration', 'slot_interval')
    def _check_slot_settings(self):
        for record in self:
            if record.slot_duration <= 0:
                raise ValidationError(_('Slot duration must be a positive number.'))
            if record.slot_interval <= 0:
                raise ValidationError(_('Slot interval must be a positive number.'))

    @api.constrains('advance_days')
    def _check_advance_days(self):
        for record in self:
            if record.advance_days < 1:
                raise ValidationError(_('Advance booking days must be at least 1.'))

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
