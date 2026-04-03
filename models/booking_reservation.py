import logging

from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)


class BookingReservation(models.Model):
    _name = 'booking.reservation'
    _description = 'Resource Reservation'
    _inherit = ['mail.thread', 'portal.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(
        string='Name',
        compute='_compute_name',
        store=True,
    )

    subject = fields.Char(
        string='Subject',
        tracking=True,
    )

    resource_type_id = fields.Many2one(
        'booking.resource.type',
        string='Resource',
        required=True,
        ondelete='restrict',
        tracking=True,
        domain="[('active', '=', True)]",
    )

    # Booking Time
    start_datetime = fields.Datetime(
        string='Start',
        required=True,
        tracking=True,
    )
    end_datetime = fields.Datetime(
        string='End',
        required=True,
        tracking=True,
    )
    duration = fields.Float(
        string='Duration (hours)',
        compute='_compute_duration',
        inverse='_inverse_duration',
        store=True,
    )

    # Booked By
    partner_id = fields.Many2one(
        'res.partner',
        string='Booked By',
        required=True,
        tracking=True,
    )

    # Organizer & Attendees (Calendar-style)
    organizer_id = fields.Many2one(
        'res.partner',
        string='Organizer',
        tracking=True,
    )
    attendee_ids = fields.Many2many(
        'res.partner',
        'booking_reservation_attendee_rel',
        'reservation_id',
        'partner_id',
        string='Attendees',
    )

    # State (no approval workflow - direct confirmation)
    state = fields.Selection(
        selection=[
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='confirmed',
        tracking=True,
    )

    # Description (Html, replaces note for new data)
    description = fields.Html(
        string='Description',
    )

    # Legacy note field kept for backward compatibility
    note = fields.Text(
        string='Notes',
    )

    # Discussion Channel
    enable_discussion = fields.Boolean(
        string='Enable Discussion',
        default=False,
    )
    channel_id = fields.Many2one(
        'discuss.channel',
        string='Discussion Channel',
        ondelete='set null',
    )

    # Reminder
    reminder_type = fields.Selection(
        selection=[
            ('none', 'None'),
            ('notification', 'Notification'),
            ('email', 'Email'),
        ],
        string='Reminder',
        default='none',
    )
    reminder_time = fields.Integer(
        string='Reminder Time (minutes)',
        default=15,
    )

    # Calendar Event Link
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        ondelete='set null',
    )

    # Related fields for display
    resource_location = fields.Char(
        related='resource_type_id.location',
        string='Location',
    )
    resource_capacity = fields.Integer(
        related='resource_type_id.capacity',
        string='Capacity',
    )
    resource_description = fields.Html(
        related='resource_type_id.description',
        string='Resource Description',
    )
    resource_enable_discussion = fields.Boolean(
        related='resource_type_id.enable_discussion',
        string='Resource Allows Discussion',
    )

    _sql_constraints = [
        (
            'check_dates',
            'CHECK(end_datetime > start_datetime)',
            'End time must be after start time.',
        ),
    ]

    @api.depends('resource_type_id', 'start_datetime', 'subject')
    def _compute_name(self):
        for record in self:
            if record.subject:
                record.name = record.subject
            elif record.resource_type_id and record.start_datetime:
                start_str = fields.Datetime.to_datetime(record.start_datetime).strftime('%Y-%m-%d %H:%M')
                record.name = f'{record.resource_type_id.name} - {start_str}'
            else:
                record.name = _('New Reservation')

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for record in self:
            if record.start_datetime and record.end_datetime:
                start = fields.Datetime.to_datetime(record.start_datetime)
                end = fields.Datetime.to_datetime(record.end_datetime)
                delta = end - start
                record.duration = delta.total_seconds() / 3600
            else:
                record.duration = 0

    def _inverse_duration(self):
        for record in self:
            if record.start_datetime and record.duration:
                from datetime import timedelta
                start = fields.Datetime.to_datetime(record.start_datetime)
                record.end_datetime = start + timedelta(hours=record.duration)

    @api.constrains('resource_type_id', 'partner_id')
    def _check_partner_access(self):
        """Ensure the partner has access to book this resource."""
        for record in self:
            if not record.resource_type_id._check_partner_access(record.partner_id):
                raise ValidationError(
                    _('Contact "%s" is not authorized to book resource "%s".') % (
                        record.partner_id.name,
                        record.resource_type_id.name,
                    )
                )

    @api.constrains('resource_type_id', 'start_datetime', 'end_datetime', 'state')
    def _check_no_overlap(self):
        """Ensure no overlapping reservations for the same resource."""
        for record in self:
            if record.state == 'cancelled':
                continue

            domain = [
                ('id', '!=', record.id),
                ('resource_type_id', '=', record.resource_type_id.id),
                ('state', '=', 'confirmed'),
                ('start_datetime', '<', record.end_datetime),
                ('end_datetime', '>', record.start_datetime),
            ]

            overlapping = self.search_count(domain)
            if overlapping:
                raise ValidationError(
                    _('This time slot is already booked for resource "%s". Please select a different time.') % (
                        record.resource_type_id.name,
                    )
                )

    def action_cancel(self):
        """Cancel the reservation."""
        self.write({'state': 'cancelled'})

    def action_confirm(self):
        """Confirm the reservation (re-confirm after cancellation)."""
        for record in self:
            # Re-check for overlaps before confirming
            record._check_no_overlap()
        self.write({'state': 'confirmed'})

    def _compute_access_url(self):
        """Compute portal access URL."""
        for record in self:
            record.access_url = f'/my/bookings/{record.id}'

    def _create_discussion_channel(self):
        """Create a discuss.channel for this reservation if enabled."""
        self.ensure_one()
        if not self.enable_discussion or self.channel_id:
            return

        # Check if discuss.channel model exists (cs_portal_discuss may not be installed)
        if 'discuss.channel' not in self.env:
            return

        channel_name = self.subject or self.name
        resource_name = self.resource_type_id.name
        full_name = f'[{resource_name}] {channel_name}'

        # Collect members: organizer + attendees + partner_id
        members = self.env['res.partner']
        if self.organizer_id:
            members |= self.organizer_id
        if self.attendee_ids:
            members |= self.attendee_ids
        if self.partner_id:
            members |= self.partner_id

        try:
            channel = self.env['discuss.channel'].sudo().create({
                'name': full_name,
                'channel_type': 'channel',
                'group_public_id': self.env.ref('base.group_portal').id,
            })
            # Add members to the channel
            for partner in members:
                channel.sudo().add_members(partner.ids)

            self.channel_id = channel
        except Exception as e:
            _logger.warning('Failed to create discussion channel for reservation %s: %s', self.id, e)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle defaults and discussion channel."""
        for vals in vals_list:
            # Default organizer to creator's partner
            if not vals.get('organizer_id') and not vals.get('partner_id'):
                pass
            elif not vals.get('organizer_id'):
                vals['organizer_id'] = vals.get('partner_id')

        reservations = super().create(vals_list)

        for reservation in reservations:
            if reservation.enable_discussion and reservation.resource_enable_discussion:
                reservation._create_discussion_channel()

        return reservations

    def write(self, vals):
        """Override write to handle discussion channel creation."""
        result = super().write(vals)

        if vals.get('enable_discussion'):
            for record in self:
                if record.enable_discussion and record.resource_enable_discussion and not record.channel_id:
                    record._create_discussion_channel()

        return result
