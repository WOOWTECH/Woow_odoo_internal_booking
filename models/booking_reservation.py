import logging

from odoo import api, fields, models
from odoo.exceptions import AccessError, ValidationError
from odoo.tools.translate import _

_logger = logging.getLogger(__name__)

# Fields of a reservation that portal (share) users may never change through
# a direct ORM call (JSON-RPC call_kw). Portal users keep the write ACL only
# because the portal chatter (/mail/message/post) requires write access on the
# document; every legitimate change goes through the portal controllers, which
# validate the input and then write with sudo().
PORTAL_PROTECTED_FIELDS = frozenset({
    'name', 'subject', 'resource_type_id', 'start_datetime', 'end_datetime',
    'duration', 'partner_id', 'organizer_id', 'attendee_ids', 'state',
    'resource_properties', 'description', 'note', 'enable_discussion',
    'channel_id', 'reminder_type', 'reminder_time', 'calendar_event_id',
    'access_token',
    # followers / messages go through the guarded mail.thread API only
    'message_follower_ids', 'message_partner_ids', 'message_ids',
    'website_message_ids',
})


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

    # ------------------------------------------------------------
    # Portal (share user) helpers
    # ------------------------------------------------------------

    def _is_portal_booker(self):
        """True when the current user is a portal/share user.

        ``sudo()`` keeps ``env.user``, so the portal controllers (which write
        with sudo) are still recognised as portal requests.
        """
        return bool(self.env.user.share)

    @api.model
    def _get_portal_attendee_domain(self, partner):
        """Contacts a portal booker may invite as attendees.

        Shared by the attendee search (/my/booking/attendees/search) and the
        attendee validation, so both always agree:

        * partners of active internal users (share=False), and
        * contacts of the booker's own commercial entity
          (same commercial_partner_id),

        never the booker, companies or archived contacts.
        """
        commercial = partner.commercial_partner_id or partner
        return [
            ('id', '!=', partner.id),
            ('active', '=', True),
            ('is_company', '=', False),
            '|',
            ('user_ids', 'any', [('share', '=', False), ('active', '=', True)]),
            ('commercial_partner_id', '=', commercial.id),
        ]

    @api.model
    def _filter_portal_attendees(self, partner, partner_ids):
        """Return the subset of ``partner_ids`` the booker may invite."""
        if not partner_ids:
            return self.env['res.partner']
        domain = [('id', 'in', list(partner_ids))] + self._get_portal_attendee_domain(partner)
        return self.env['res.partner'].sudo().search(domain)

    @api.model
    def _is_portal_slot(self, resource, start_local, end_local):
        """True when [start_local, end_local) (naive, resource timezone) is
        exactly one of the slots offered by ``resource._generate_slots``.

        The comparison is exact: a start or end that is off the grid by even
        a second is refused (a booking ending at 11:00:59 would otherwise
        also block the next slot). The slot values are compared at the
        precision the portal posts them (whole seconds, see the slot links).
        """
        if not resource or not start_local or not end_local:
            return False
        day = start_local.date()
        for slot in resource.sudo()._generate_slots(day, day):
            if (slot['start'].replace(microsecond=0) == start_local
                    and slot['end'].replace(microsecond=0) == end_local):
                return True
        return False

    @api.constrains('attendee_ids')
    def _check_portal_attendees(self):
        """Portal bookers may only invite contacts from the shared attendee
        domain (internal users, own commercial entity)."""
        if not self._is_portal_booker():
            return
        requester = self.env.user.partner_id
        for record in self:
            invited = record.sudo().attendee_ids - requester
            if not invited:
                continue
            allowed = self._filter_portal_attendees(requester, invited.ids)
            if invited - allowed:
                raise ValidationError(
                    _('You can only invite your colleagues or internal users as attendees.')
                )

    @api.constrains('resource_type_id', 'start_datetime', 'end_datetime')
    def _check_portal_slot_alignment(self):
        """Portal bookings must match a slot of the resource's availability
        grid (availability_ids + slot_interval, resource timezone). Backend
        users keep free scheduling."""
        if not self._is_portal_booker():
            return
        for record in self:
            if record.state == 'cancelled' or not record.start_datetime or not record.end_datetime:
                continue
            resource = record.sudo().resource_type_id
            # the grid lives in the resource timezone, never in the portal
            # user's own (self-writeable) timezone
            start_local = resource._booking_utc_to_local(record.start_datetime)
            end_local = resource._booking_utc_to_local(record.end_datetime)
            if not self._is_portal_slot(resource, start_local, end_local):
                raise ValidationError(
                    _('The selected time is not an available slot of resource "%s".')
                    % (resource.name or '')
                )

    def _lock_resources_for_booking(self):
        """Serialise bookings per resource.

        Touch the booking_resource_type row of every resource involved with a
        real (no-op) UPDATE before the overlap check. Two transactions booking
        the same resource then queue on that row lock, and the later one fails
        with a serialization error (REPEATABLE READ: the row was updated by a
        transaction that committed after its snapshot); Odoo retries the
        request with a fresh snapshot and the overlap check then sees the
        first booking. A plain SELECT ... FOR UPDATE / advisory lock would only
        make the second transaction wait and then check against its stale
        snapshot. FOR NO KEY UPDATE (taken by this UPDATE) does not conflict
        with the KEY SHARE lock the reservation INSERT holds on the resource,
        so two concurrent creates cannot deadlock on it.
        """
        resource_ids = sorted(set(self.mapped('resource_type_id').ids))
        if not resource_ids:
            return
        self.env.cr.execute(
            "UPDATE booking_resource_type SET write_date = write_date WHERE id IN %s",
            [tuple(resource_ids)],
        )

    @api.constrains('resource_type_id', 'start_datetime', 'end_datetime', 'state')
    def _check_no_overlap(self):
        """Ensure no overlapping reservations for the same resource.

        Bookings are serialised per resource (see _lock_resources_for_booking)
        before the parameterised overlap query, so concurrent requests for the
        same slot cannot both be committed.
        """
        self.filtered(lambda r: r.state != 'cancelled')._lock_resources_for_booking()
        for record in self:
            if record.state == 'cancelled':
                continue

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

        # Check if discuss.channel model exists (woow_odoo_portal_discuss may not be installed)
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
            # A members-only conversation: core record rules only let members
            # read/join a non-'channel' discuss.channel, whereas a 'channel'
            # with group_public_id=base.group_portal is readable and joinable
            # by every portal user through the core /discuss/channel/* routes.
            channel = self.env['discuss.channel'].sudo().create({
                'name': full_name,
                'channel_type': 'group',
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

    def _check_portal_direct_write(self, field_names):
        """Refuse direct (non-sudo) ORM changes of reservation fields by
        portal users; the portal controllers validate and write with sudo."""
        if self.env.su or not self._is_portal_booker():
            return
        forbidden = PORTAL_PROTECTED_FIELDS.intersection(field_names)
        if forbidden:
            raise AccessError(
                _('Portal users cannot modify reservations directly (%s).')
                % ', '.join(sorted(forbidden))
            )

    # ------------------------------------------------------------
    # Mail recipients of portal users
    # ------------------------------------------------------------
    # Portal users keep the write ACL for the portal chatter, which is also
    # what the public mail.thread API (message_subscribe, message_post,
    # message_notify ... callable through /web/dataset/call_kw) checks. Without
    # the guards below a portal booker could make any partner of the database
    # a follower or a recipient of their reservation and have it e-mailed on
    # every chatter post (the attendee check, by another field).

    def _portal_mail_guard_active(self):
        """Direct (non-sudo) mail.thread calls of a portal/share user."""
        return not self.env.su and self._is_portal_booker()

    def _get_portal_allowed_recipients(self, partner_ids):
        """Subset of ``partner_ids`` a portal user may add as followers /
        recipients of ``self``: themselves, the participants of the
        reservations and the contacts of the shared attendee domain."""
        requester = self.env.user.partner_id
        wanted = {
            pid for pid in partner_ids
            if isinstance(pid, int) and not isinstance(pid, bool) and 0 < pid < 2 ** 31
        }
        allowed = requester
        for record in self.sudo():
            allowed |= record.partner_id | record.organizer_id | record.attendee_ids
        candidates = list(wanted - set(allowed.ids))
        if candidates:
            allowed |= self.env['res.partner'].sudo().search(
                [('id', 'in', candidates)] + self._get_portal_attendee_domain(requester))
        return allowed.filtered(lambda p: p.id in wanted)

    def _filter_portal_recipient_ids(self, partner_ids):
        """Keep only the allowed partner ids (order kept)."""
        if not partner_ids or not self._portal_mail_guard_active():
            return partner_ids
        allowed = set(self._get_portal_allowed_recipients(partner_ids).ids)
        kept = [pid for pid in partner_ids if pid in allowed]
        if len(kept) != len(partner_ids):
            _logger.info(
                'booking.reservation %s: portal user %s tried to add recipients %r; dropped',
                self.ids, self.env.uid, [pid for pid in partner_ids if pid not in allowed])
        return kept

    def message_subscribe(self, partner_ids=None, subtype_ids=None):
        if partner_ids and self._portal_mail_guard_active():
            partner_ids = self._filter_portal_recipient_ids(list(partner_ids))
            if not partner_ids:
                return True
        return super().message_subscribe(partner_ids=partner_ids, subtype_ids=subtype_ids)

    def message_unsubscribe(self, partner_ids=None):
        if (partner_ids and self._portal_mail_guard_active()
                and set(partner_ids) != {self.env.user.partner_id.id}):
            raise AccessError(_('Portal users can only unfollow reservations themselves.'))
        return super().message_unsubscribe(partner_ids=partner_ids)

    def message_post(self, *, partner_ids=None, **kwargs):
        if partner_ids and self._portal_mail_guard_active():
            partner_ids = self._filter_portal_recipient_ids(list(partner_ids))
        return super().message_post(partner_ids=partner_ids, **kwargs)

    def message_notify(self, *, partner_ids=False, **kwargs):
        if partner_ids and self._portal_mail_guard_active():
            partner_ids = self._filter_portal_recipient_ids(list(partner_ids))
        return super().message_notify(partner_ids=partner_ids, **kwargs)

    @api.model_create_multi
    def create(self, vals_list):
        """Override create to handle defaults and discussion channel."""
        for vals in vals_list:
            self._check_portal_direct_write(vals.keys())
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
        self._check_portal_direct_write(vals.keys())
        result = super().write(vals)

        if vals.get('enable_discussion'):
            for record in self:
                if record.enable_discussion and record.resource_enable_discussion and not record.channel_id:
                    record._create_discussion_channel()

        return result
