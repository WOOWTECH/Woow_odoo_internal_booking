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

    # Booking time
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
        string='Duration (Hours)',
        compute='_compute_duration',
        inverse='_inverse_duration',
        store=True,
    )

    # Booker
    partner_id = fields.Many2one(
        'res.partner',
        string='Booker',
        required=True,
        ondelete='restrict',
        tracking=True,
    )

    # Organizer & Attendees
    organizer_id = fields.Many2one(
        'res.partner',
        string='Organizer',
        ondelete='set null',
        tracking=True,
    )
    attendee_ids = fields.Many2many(
        'res.partner',
        'booking_reservation_attendee_rel',
        'reservation_id',
        'partner_id',
        string='Attendees',
    )

    # State
    state = fields.Selection(
        selection=[
            ('confirmed', 'Confirmed'),
            ('cancelled', 'Cancelled'),
        ],
        string='State',
        default='confirmed',
        tracking=True,
    )

    # Dynamic properties (values per reservation, definition from resource)
    resource_properties = fields.Properties(
        string='Properties',
        definition='resource_type_id.resource_properties_definition',
        copy=True,
    )

    # Description
    description = fields.Html(
        string='Description',
    )

    # Legacy note field
    note = fields.Text(
        string='Note',
    )

    # Discussion channel
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
        string='Reminder Time (Minutes)',
        default=15,
    )

    # Calendar event link
    calendar_event_id = fields.Many2one(
        'calendar.event',
        string='Calendar Event',
        ondelete='set null',
    )

    # Related fields
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

    @api.constrains('start_datetime', 'end_datetime')
    def _check_start_before_end(self):
        """Ensure start datetime is strictly before end datetime."""
        for record in self:
            if record.start_datetime and record.end_datetime:
                if record.start_datetime >= record.end_datetime:
                    raise ValidationError(
                        _('End time must be after start time.')
                    )

    @api.constrains('resource_type_id', 'start_datetime', 'end_datetime')
    def _check_duration_matches_slot(self):
        """Ensure booking duration matches the resource's configured slot_duration."""
        for record in self:
            if not record.start_datetime or not record.end_datetime:
                continue
            start = fields.Datetime.to_datetime(record.start_datetime)
            end = fields.Datetime.to_datetime(record.end_datetime)
            actual_hours = (end - start).total_seconds() / 3600
            expected_hours = record.resource_type_id.slot_duration
            # Allow small floating-point tolerance (1 minute)
            if abs(actual_hours - expected_hours) > (1.0 / 60):
                raise ValidationError(
                    _('Booking duration (%(actual).1f hours) does not match '
                      'the slot duration (%(expected).1f hours) of resource "%(resource)s".') % {
                        'actual': actual_hours,
                        'expected': expected_hours,
                        'resource': record.resource_type_id.name or '',
                    }
                )

    @api.constrains('resource_type_id', 'partner_id')
    def _check_partner_access(self):
        """Ensure the partner has access to book this resource."""
        for record in self:
            if not record.resource_type_id._check_partner_access(record.partner_id):
                raise ValidationError(
                    _('Contact "%(partner)s" does not have permission to book resource "%(resource)s".') % {
                        'partner': record.partner_id.name or '',
                        'resource': record.resource_type_id.name or '',
                    }
                )

    @api.constrains('resource_type_id', 'start_datetime', 'end_datetime', 'state')
    def _check_no_overlap(self):
        """Ensure no overlapping reservations for the same resource.

        Uses a raw SQL query with FOR UPDATE to prevent race conditions
        from concurrent booking attempts. The second concurrent transaction
        will block until the first commits, then correctly detect the overlap.
        """
        for record in self:
            if record.state == 'cancelled':
                continue

            # Use SQL with row-level locking to prevent race conditions
            self.env.cr.execute("""
                SELECT id FROM booking_reservation
                WHERE id != %s
                  AND resource_type_id = %s
                  AND state = 'confirmed'
                  AND start_datetime < %s
                  AND end_datetime > %s
                FOR UPDATE
                LIMIT 1
            """, (record.id, record.resource_type_id.id,
                  record.end_datetime, record.start_datetime))

            if self.env.cr.fetchone():
                raise ValidationError(
                    _('This time slot for resource "%s" is already booked. Please choose another time.') % (
                        record.resource_type_id.name,
                    )
                )

    def action_open_discuss_channel(self):
        """Open the discussion channel directly in the Discuss chat interface."""
        self.ensure_one()
        if not self.channel_id:
            return False
        return {
            'type': 'ir.actions.act_url',
            'url': '/odoo/discuss?active_id=discuss.channel_%s' % self.channel_id.id,
            'target': 'self',
        }

    def action_cancel(self):
        """Cancel the reservation."""
        self.write({'state': 'cancelled'})
        for record in self:
            record._send_booking_email('odoo_booking_reservation.mail_template_booking_cancelled')
        return True

    def action_confirm(self):
        """Confirm the reservation (re-confirm after cancellation).

        Manually checks overlap before writing state.
        The @api.constrains also fires on write, but this pre-check
        provides a clearer error path before the state transition.
        """
        for record in self:
            if record.state == 'confirmed':
                continue
            record._check_no_overlap()
        to_confirm = self.filtered(lambda r: r.state != 'confirmed')
        to_confirm.write({'state': 'confirmed'})
        for record in to_confirm:
            if not record.calendar_event_id:
                record._create_calendar_event()
        return True

    def _compute_access_url(self):
        """Compute portal access URL."""
        for record in self:
            record.access_url = f'/my/bookings/{record.id}'

    def _send_booking_email(self, template_xmlid):
        """Send a booking email using the given template."""
        self.ensure_one()
        template = self.env.ref(template_xmlid, raise_if_not_found=False)
        if not template:
            return
        try:
            template.send_mail(self.id, force_send=False)
        except Exception as e:
            _logger.warning('Failed to send booking email for reservation %s: %s', self.id, e)

    def _create_calendar_event(self):
        """Create a linked calendar.event for this reservation."""
        self.ensure_one()
        if self.calendar_event_id:
            return

        # Build attendee partner list
        attendee_partners = self.env['res.partner']
        if self.partner_id:
            attendee_partners |= self.partner_id
        if self.organizer_id and self.organizer_id != self.partner_id:
            attendee_partners |= self.organizer_id
        if self.attendee_ids:
            attendee_partners |= self.attendee_ids

        event_name = self.name or self.subject or _('Reservation')
        vals = {
            'name': event_name,
            'start': self.start_datetime,
            'stop': self.end_datetime,
            'partner_ids': [(6, 0, attendee_partners.ids)],
            'description': self.description or '',
            'location': self.resource_location or '',
        }

        try:
            event = self.env['calendar.event'].sudo().create(vals)
            self.calendar_event_id = event
        except Exception as e:
            _logger.warning(
                'Failed to create calendar event for reservation %s: %s',
                self.id, e,
            )

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

    @api.constrains('start_datetime')
    def _check_not_in_past(self):
        """Prevent creating reservations in the past."""
        for record in self:
            if record.state == 'cancelled':
                continue
            if record.start_datetime and record.start_datetime < fields.Datetime.now():
                raise ValidationError(
                    _('Cannot book a time slot in the past.')
                )

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
            if reservation.state == 'confirmed':
                reservation._create_calendar_event()
            reservation._send_booking_email('odoo_booking_reservation.mail_template_booking_confirmed')

        return reservations

    def write(self, vals):
        """Override write to handle discussion channel creation."""
        result = super().write(vals)

        if vals.get('enable_discussion'):
            for record in self:
                if record.enable_discussion and record.resource_enable_discussion and not record.channel_id:
                    record._create_discussion_channel()

        return result
