from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


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
        store=True,
    )

    # Booked By
    partner_id = fields.Many2one(
        'res.partner',
        string='Booked By',
        required=True,
        tracking=True,
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

    # Additional Info
    note = fields.Text(
        string='Notes',
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

    _sql_constraints = [
        (
            'check_dates',
            'CHECK(end_datetime > start_datetime)',
            'End time must be after start time.',
        ),
    ]

    @api.depends('resource_type_id', 'start_datetime')
    def _compute_name(self):
        for record in self:
            if record.resource_type_id and record.start_datetime:
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

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle any additional logic."""
        reservations = super().create(vals_list)
        # Could add calendar event creation here if needed
        return reservations

    def write(self, vals):
        """Override write to handle state changes."""
        result = super().write(vals)
        # Could add calendar event update here if needed
        return result
