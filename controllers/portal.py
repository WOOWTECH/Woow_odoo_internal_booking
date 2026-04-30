from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError, ValidationError
from odoo.tools import html_sanitize
from datetime import datetime, timedelta
import json
import pytz


class BookingPortal(CustomerPortal):
    """
    Portal Controller for Resource Booking.
    Does not depend on website module - uses portal.portal_layout template.
    """

    def _get_local_now(self):
        """Get current datetime in the user's timezone (naive, for comparison with slot times)."""
        tz_name = request.env.user.tz or request.env.context.get('tz') or 'UTC'
        try:
            user_tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.UTC
        return datetime.now(pytz.UTC).astimezone(user_tz).replace(tzinfo=None)

    def _prepare_home_portal_values(self, counters):
        """Add booking counts to portal home."""
        values = super()._prepare_home_portal_values(counters)
        if 'booking_count' in counters:
            partner = request.env.user.partner_id
            values['booking_count'] = request.env['booking.reservation'].sudo().search_count([
                ('partner_id', '=', partner.id),
                ('state', '=', 'confirmed'),
            ])
        return values

    def _get_accessible_resources(self, partner):
        """Get resources that the partner is allowed to book."""
        return request.env['booking.resource.type'].sudo().search([
            ('active', '=', True),
            '|',
            ('share_type', '=', 'all'),
            ('allowed_partner_ids', 'in', [partner.id]),
        ])

    def _check_resource_access(self, resource, partner):
        """Check if partner has access to the resource."""
        if not resource or not resource.active:
            return False
        return resource._check_partner_access(partner)

    def _generate_slots_for_portal(self, resource, date_from, date_to, partner):
        """
        Generate available time slots for Portal display.
        Hides booking details from other users (privacy).

        Slots are generated in the user's local timezone. Reservations in the DB
        are stored in UTC. We convert between the two for correct overlap detection.
        """
        slots = resource._generate_slots(date_from, date_to)

        # Determine user timezone for converting between local and UTC
        tz_name = request.env.user.tz or request.env.context.get('tz') or 'UTC'
        try:
            user_tz = pytz.timezone(tz_name)
        except pytz.UnknownTimeZoneError:
            user_tz = pytz.UTC

        # Convert date range boundaries from local time to UTC for DB query
        window_start_local = datetime.combine(date_from, datetime.min.time())
        window_end_local = datetime.combine(date_to, datetime.max.time())
        window_start_utc = user_tz.localize(window_start_local).astimezone(pytz.UTC).replace(tzinfo=None)
        window_end_utc = user_tz.localize(window_end_local).astimezone(pytz.UTC).replace(tzinfo=None)

        # Use overlap query (not fully-contained) to catch boundary-straddling reservations
        reservations = request.env['booking.reservation'].sudo().search([
            ('resource_type_id', '=', resource.id),
            ('state', '=', 'confirmed'),
            ('start_datetime', '<', window_end_utc),
            ('end_datetime', '>', window_start_utc),
        ])

        # Mark slot availability
        for slot in slots:
            slot['is_available'] = True
            slot['is_mine'] = False
            slot['reservation_id'] = False

            for res in reservations:
                # Convert reservation UTC times to local for comparison with local slots
                res_start_utc = fields.Datetime.to_datetime(res.start_datetime)
                res_end_utc = fields.Datetime.to_datetime(res.end_datetime)
                res_start_local = pytz.UTC.localize(res_start_utc).astimezone(user_tz).replace(tzinfo=None)
                res_end_local = pytz.UTC.localize(res_end_utc).astimezone(user_tz).replace(tzinfo=None)

                # Check overlap (both sides now in local time)
                if slot['start'] < res_end_local and slot['end'] > res_start_local:
                    slot['is_available'] = False
                    if res.partner_id.id == partner.id:
                        slot['is_mine'] = True
                        slot['reservation_id'] = res.id
                    break

        return slots

    # ============================================================
    # RESOURCE LIST
    # ============================================================

    @http.route('/my/booking/resources', type='http', auth='user', website=True)
    def portal_my_resources(self, **kw):
        """Display list of resources available to the user."""
        partner = request.env.user.partner_id
        resources = self._get_accessible_resources(partner)

        values = {
            'resources': resources,
            'page_name': 'booking_resources',
        }

        return request.render('odoo_booking_reservation.portal_my_resources', values)

    # ============================================================
    # INTERNAL RESOURCES (Integrated Page)
    # ============================================================

    @http.route(['/my/internal-resources', '/my/internal-resources/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_internal_resources(self, page=1, sortby='date_desc', filterby='upcoming', **kw):
        """Display integrated page: resources + bookings."""
        partner = request.env.user.partner_id

        # Resources section
        resources = self._get_accessible_resources(partner)

        # Bookings section
        Reservation = request.env['booking.reservation'].sudo()
        domain = [('partner_id', '=', partner.id)]

        filter_options = {
            'all': {'label': _('All'), 'domain': []},
            'upcoming': {'label': _('Upcoming'), 'domain': [('start_datetime', '>=', fields.Datetime.now()), ('state', '=', 'confirmed')]},
            'past': {'label': _('Past'), 'domain': [('start_datetime', '<', fields.Datetime.now())]},
            'confirmed': {'label': _('Confirmed'), 'domain': [('state', '=', 'confirmed')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
        }

        if filterby not in filter_options:
            filterby = 'upcoming'
        domain += filter_options[filterby]['domain']

        sort_options = {
            'date_desc': {'label': _('Date (Newest)'), 'order': 'start_datetime desc'},
            'date_asc': {'label': _('Date (Oldest)'), 'order': 'start_datetime asc'},
            'resource': {'label': _('Resource'), 'order': 'resource_type_id, start_datetime desc'},
        }

        if sortby not in sort_options:
            sortby = 'date_desc'
        order = sort_options[sortby]['order']

        booking_count = Reservation.search_count(domain)
        pager = portal_pager(
            url='/my/internal-resources',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=booking_count,
            page=page,
            step=10,
        )

        reservations = Reservation.search(
            domain,
            order=order,
            limit=10,
            offset=pager['offset'],
        )

        values = {
            'resources': resources,
            'reservations': reservations,
            'pager': pager,
            'sortby': sortby,
            'filterby': filterby,
            'sort_options': sort_options,
            'filter_options': filter_options,
            'page_name': 'internal_resources',
        }

        return request.render('odoo_booking_reservation.portal_internal_resources', values)

    # ============================================================
    # RESOURCE DETAIL & BOOKING
    # ============================================================

    @http.route('/my/booking/resources/<int:resource_id>', type='http', auth='user', website=True)
    def portal_resource_detail(self, resource_id, date=None, **kw):
        """Display resource details and available slots."""
        partner = request.env.user.partner_id
        resource = request.env['booking.resource.type'].sudo().browse(resource_id)

        if not self._check_resource_access(resource, partner):
            raise AccessError(_("You do not have permission to access this resource."))

        # Date range for slots (use local timezone so "today" matches user's wall clock)
        local_now = self._get_local_now()
        today = local_now.date()
        max_date = today + timedelta(days=resource.advance_days)

        if date:
            try:
                selected_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                selected_date = today

            # Clamp: do not allow browsing past dates
            if selected_date < today:
                selected_date = today
            # Clamp: do not allow browsing beyond advance_days
            if selected_date > max_date:
                selected_date = max_date
        else:
            selected_date = today

        # Show one week of slots, but cap at max_date
        date_from = selected_date
        date_to = min(selected_date + timedelta(days=7), max_date + timedelta(days=1))

        slots = self._generate_slots_for_portal(resource, date_from, date_to, partner)

        # Group slots by date
        slots_by_date = {}
        for slot in slots:
            date_key = slot['date_str']
            if date_key not in slots_by_date:
                slots_by_date[date_key] = []
            slots_by_date[date_key].append(slot)

        values = {
            'resource': resource,
            'slots': slots,
            'slots_by_date': slots_by_date,
            'selected_date': selected_date,
            'date_from': date_from,
            'date_to': date_to,
            'date_from_str': date_from.strftime('%Y/%m/%d'),
            'date_to_str': date_to.strftime('%Y/%m/%d'),
            'prev_week': max(today, date_from - timedelta(days=7)).strftime('%Y-%m-%d'),
            'next_week': min(max_date, date_from + timedelta(days=7)).strftime('%Y-%m-%d'),
            'show_prev': date_from > today,
            'show_next': date_from + timedelta(days=7) < max_date,
            'page_name': 'booking_resource_detail',
            'error': kw.get('error'),
        }

        return request.render('odoo_booking_reservation.portal_resource_detail', values)

    @http.route('/my/booking/attendees/search', type='json', auth='user')
    def portal_search_attendees(self, query='', **kw):
        """API: Search same-company partners for attendee selection."""
        partner = request.env.user.partner_id
        company = request.env.user.company_id

        if not company:
            return {'attendees': []}

        domain = [
            ('id', '!=', partner.id),
            ('is_company', '=', False),
            '|',
            ('company_id', '=', company.id),
            ('parent_id', '=', company.partner_id.id),
        ]
        if query:
            domain = [('name', 'ilike', query)] + domain

        partners = request.env['res.partner'].sudo().search(domain, limit=20, order='name')
        return {
            'attendees': [
                {'id': p.id, 'name': p.name, 'email': p.email or ''}
                for p in partners
            ]
        }

    @http.route('/my/booking/resources/<int:resource_id>/slots', type='json', auth='user')
    def portal_get_slots(self, resource_id, date_from=None, date_to=None, **kw):
        """API: Get available slots for a resource (JSON)."""
        partner = request.env.user.partner_id
        resource = request.env['booking.resource.type'].sudo().browse(resource_id)

        if not self._check_resource_access(resource, partner):
            return {'error': 'Unauthorized'}

        local_now = self._get_local_now()
        today = local_now.date()
        max_date = today + timedelta(days=resource.advance_days)

        if date_from:
            try:
                date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return {'error': 'invalid_date_format'}
        else:
            date_from = today

        if date_to:
            try:
                date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return {'error': 'invalid_date_format'}
        else:
            date_to = date_from + timedelta(days=7)

        # Clamp to valid range
        if date_from < today:
            date_from = today
        if date_to > max_date + timedelta(days=1):
            date_to = max_date + timedelta(days=1)

        slots = self._generate_slots_for_portal(resource, date_from, date_to, partner)

        # Convert datetime objects to strings for JSON
        for slot in slots:
            slot['start'] = slot['start'].isoformat()
            slot['end'] = slot['end'].isoformat()

        return {'slots': slots}

    # ============================================================
    # CREATE BOOKING
    # ============================================================

    @http.route('/my/bookings/new', type='http', auth='user', website=True)
    def portal_new_booking(self, resource_id=None, **kw):
        """New booking page - select resource."""
        partner = request.env.user.partner_id
        resources = self._get_accessible_resources(partner)

        if not resources:
            return request.render('odoo_booking_reservation.portal_no_resources')

        selected_resource = None
        if resource_id:
            selected_resource = resources.filtered(lambda r: r.id == int(resource_id))

        values = {
            'resources': resources,
            'selected_resource': selected_resource[:1] if selected_resource else None,
            'page_name': 'booking_new',
            'error': kw.get('error'),
        }

        return request.render('odoo_booking_reservation.portal_new_booking', values)

    @http.route('/my/bookings/confirm', type='http', auth='user', website=True)
    def portal_confirm_booking(self, **kw):
        """Display booking confirmation page before creating the reservation."""
        partner = request.env.user.partner_id

        resource_id = kw.get('resource_id')
        start_datetime_str = kw.get('start_datetime')
        end_datetime_str = kw.get('end_datetime')

        if not resource_id or not start_datetime_str or not end_datetime_str:
            return request.redirect('/my/bookings/new?error=missing_fields')

        try:
            resource_id = int(resource_id)
        except (ValueError, TypeError):
            return request.redirect('/my/bookings/new?error=invalid_resource')

        resource = request.env['booking.resource.type'].sudo().browse(resource_id)
        if not resource.exists():
            return request.redirect('/my/bookings/new?error=invalid_resource')

        if not self._check_resource_access(resource, partner):
            return request.redirect('/my/bookings/new?error=unauthorized')

        try:
            start_dt = datetime.strptime(start_datetime_str, '%Y-%m-%d %H:%M:%S')
            end_dt = datetime.strptime(end_datetime_str, '%Y-%m-%d %H:%M:%S')
        except (ValueError, TypeError):
            return request.redirect('/my/booking/resources/%s?error=invalid_datetime' % resource_id)

        # Reject past bookings (compare in user's local timezone since slot times are local)
        local_now = self._get_local_now()
        if start_dt < local_now:
            return request.redirect('/my/booking/resources/%s?error=past_slot' % resource_id)

        # Reject bookings beyond advance_days
        max_date = local_now + timedelta(days=resource.advance_days)
        if start_dt > max_date:
            return request.redirect('/my/booking/resources/%s?error=too_far_ahead' % resource_id)

        duration_hours = (end_dt - start_dt).total_seconds() / 3600

        values = {
            'resource': resource,
            'start_datetime': start_datetime_str,
            'end_datetime': end_datetime_str,
            'start_dt': start_dt,
            'end_dt': end_dt,
            'duration': duration_hours,
            'partner': partner,
            'page_name': 'booking_confirm',
        }
        return request.render('odoo_booking_reservation.portal_booking_confirm', values)

    @http.route('/my/bookings/create', type='http', auth='user', methods=['POST'], website=True)
    def portal_create_booking(self, **post):
        """Create a new booking."""
        partner = request.env.user.partner_id

        try:
            resource_id = int(post.get('resource_id', 0))
            start_datetime = post.get('start_datetime')
            end_datetime = post.get('end_datetime')
            subject = post.get('subject', '').strip()
            description = post.get('description', '').strip()
            enable_discussion = post.get('enable_discussion') == 'on'

            if not resource_id or not start_datetime or not end_datetime:
                return request.redirect('/my/bookings/new?error=missing_fields')

            resource = request.env['booking.resource.type'].sudo().browse(resource_id)

            if not resource.exists():
                return request.redirect('/my/bookings/new?error=invalid_resource')

            if not self._check_resource_access(resource, partner):
                return request.redirect('/my/bookings/new?error=unauthorized')

            # Reject past or too-far-ahead bookings (use local timezone)
            try:
                start_dt = datetime.strptime(start_datetime, '%Y-%m-%d %H:%M:%S')
                local_now = self._get_local_now()
                if start_dt < local_now:
                    return request.redirect('/my/booking/resources/%s?error=past_slot' % resource_id)
                max_date = local_now + timedelta(days=resource.advance_days)
                if start_dt > max_date:
                    return request.redirect('/my/booking/resources/%s?error=too_far_ahead' % resource_id)
            except (ValueError, TypeError):
                return request.redirect('/my/bookings/new?error=invalid_datetime')

            # Convert local datetime strings to UTC for storage
            tz_name = request.env.user.tz or request.env.context.get('tz') or 'UTC'
            try:
                user_tz = pytz.timezone(tz_name)
            except pytz.UnknownTimeZoneError:
                user_tz = pytz.UTC
            start_dt_local = user_tz.localize(start_dt)
            end_dt_local = user_tz.localize(datetime.strptime(end_datetime, '%Y-%m-%d %H:%M:%S'))
            start_dt_utc = start_dt_local.astimezone(pytz.UTC).replace(tzinfo=None)
            end_dt_utc = end_dt_local.astimezone(pytz.UTC).replace(tzinfo=None)

            # Build reservation vals (UTC datetimes for DB storage)
            vals = {
                'resource_type_id': resource_id,
                'start_datetime': fields.Datetime.to_string(start_dt_utc),
                'end_datetime': fields.Datetime.to_string(end_dt_utc),
                'partner_id': partner.id,
                'organizer_id': partner.id,
                'state': 'confirmed',
            }

            if subject:
                vals['subject'] = subject
            if description:
                vals['description'] = html_sanitize(description)
            if enable_discussion and resource.enable_discussion:
                vals['enable_discussion'] = True

            # Process attendees
            attendee_ids_str = post.get('attendee_ids', '')
            if attendee_ids_str:
                try:
                    att_ids = [int(x) for x in attendee_ids_str.split(',') if x.strip()]
                    if att_ids:
                        vals['attendee_ids'] = [(6, 0, att_ids)]
                except (ValueError, TypeError):
                    pass

            # Create reservation
            reservation = request.env['booking.reservation'].sudo().create(vals)

            return request.redirect(f'/my/bookings/{reservation.id}?success=created')

        except ValidationError:
            # Overlap or access constraint - redirect back to resource page
            return request.redirect(f'/my/booking/resources/{resource_id}?error=slot_taken')
        except Exception:
            return request.redirect('/my/bookings/new?error=system_error')

    # ============================================================
    # MY BOOKINGS LIST
    # ============================================================

    @http.route(['/my/bookings', '/my/bookings/page/<int:page>'], type='http', auth='user', website=True)
    def portal_my_bookings(self, page=1, sortby='date_desc', filterby='upcoming', **kw):
        """Display user's bookings list."""
        partner = request.env.user.partner_id
        Reservation = request.env['booking.reservation'].sudo()

        # Domain base
        domain = [('partner_id', '=', partner.id)]

        # Filter options
        filter_options = {
            'all': {'label': _('All'), 'domain': []},
            'upcoming': {'label': _('Upcoming'), 'domain': [('start_datetime', '>=', fields.Datetime.now()), ('state', '=', 'confirmed')]},
            'past': {'label': _('Past'), 'domain': [('start_datetime', '<', fields.Datetime.now())]},
            'confirmed': {'label': _('Confirmed'), 'domain': [('state', '=', 'confirmed')]},
            'cancelled': {'label': _('Cancelled'), 'domain': [('state', '=', 'cancelled')]},
        }

        if filterby not in filter_options:
            filterby = 'upcoming'

        domain += filter_options[filterby]['domain']

        # Sort options
        sort_options = {
            'date_desc': {'label': _('Date (Newest)'), 'order': 'start_datetime desc'},
            'date_asc': {'label': _('Date (Oldest)'), 'order': 'start_datetime asc'},
            'resource': {'label': _('Resource'), 'order': 'resource_type_id, start_datetime desc'},
        }

        if sortby not in sort_options:
            sortby = 'date_desc'

        order = sort_options[sortby]['order']

        # Pager
        booking_count = Reservation.search_count(domain)
        pager = portal_pager(
            url='/my/bookings',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=booking_count,
            page=page,
            step=10,
        )

        # Get reservations
        reservations = Reservation.search(
            domain,
            order=order,
            limit=10,
            offset=pager['offset'],
        )

        values = {
            'reservations': reservations,
            'pager': pager,
            'sortby': sortby,
            'filterby': filterby,
            'sort_options': sort_options,
            'filter_options': filter_options,
            'page_name': 'my_bookings',
        }

        return request.render('odoo_booking_reservation.portal_my_bookings', values)

    # ============================================================
    # BOOKING DETAIL
    # ============================================================

    @http.route('/my/bookings/<int:booking_id>', type='http', auth='user', website=True)
    def portal_booking_detail(self, booking_id, **kw):
        """Display booking details."""
        partner = request.env.user.partner_id
        reservation = request.env['booking.reservation'].sudo().browse(booking_id)

        if not reservation.exists() or reservation.partner_id.id != partner.id:
            raise MissingError(_("This reservation does not exist or you do not have access."))

        success = kw.get('success')
        error = kw.get('error')

        values = {
            'reservation': reservation,
            'object': reservation,
            'page_name': 'booking_detail',
            'success': success,
            'error': error,
        }

        return request.render('odoo_booking_reservation.portal_booking_detail', values)

    # ============================================================
    # DISCUSS CHANNEL REDIRECT
    # ============================================================

    @http.route('/my/bookings/<int:booking_id>/discuss', type='http', auth='user', website=True)
    def portal_booking_discuss(self, booking_id, **kw):
        """Redirect to the discussion channel for this booking."""
        partner = request.env.user.partner_id
        reservation = request.env['booking.reservation'].sudo().browse(booking_id)

        if not reservation.exists() or not reservation.channel_id:
            return request.redirect('/my/bookings')

        # Allow access if user is the booker, organizer, or an attendee
        allowed_partners = reservation.partner_id | reservation.organizer_id | reservation.attendee_ids
        if partner not in allowed_partners:
            return request.redirect('/my/bookings')

        # Internal users go to backend Discuss (popup dialog mode)
        # Portal users go to /my/discussions with auto-open parameter
        if request.env.user.has_group('base.group_user'):
            return request.redirect('/odoo/discuss?active_id=discuss.channel_%s' % reservation.channel_id.id)
        else:
            return request.redirect('/my/discussions?open_channel=%s' % reservation.channel_id.id)

    @http.route(['/my/discussions', '/my/discussions/page/<int:page>'], type='http', auth='user', website=True)
    def portal_discussions(self, page=1, **kw):
        """Override /my/discussions to validate open_channel parameter.

        Prevents IDOR: users can only auto-open channels linked to their own bookings.
        If open_channel is provided but the user has no booking with that channel,
        strip the parameter and show the discussions list normally.
        """
        open_channel = kw.get('open_channel')
        if open_channel:
            try:
                channel_id = int(open_channel)
            except (ValueError, TypeError):
                return request.redirect('/my/discussions')

            partner = request.env.user.partner_id
            reservation = request.env['booking.reservation'].sudo().search([
                ('channel_id', '=', channel_id),
                '|', '|',
                ('partner_id', '=', partner.id),
                ('organizer_id', '=', partner.id),
                ('attendee_ids', 'in', [partner.id]),
            ], limit=1)

            if not reservation:
                return request.redirect('/my/discussions')

        # Call parent's portal_discussions (from cs_portal_discuss)
        return super().portal_discussions(page=page, **kw)

    # ============================================================
    # CANCEL BOOKING
    # ============================================================

    @http.route('/my/bookings/<int:booking_id>/cancel', type='http', auth='user', methods=['POST'], website=True)
    def portal_cancel_booking(self, booking_id, **kw):
        """Cancel a booking."""
        partner = request.env.user.partner_id
        reservation = request.env['booking.reservation'].sudo().browse(booking_id)

        if not reservation.exists() or reservation.partner_id.id != partner.id:
            raise MissingError(_("This reservation does not exist or you do not have access."))

        if reservation.state == 'confirmed':
            reservation.action_cancel()
            return request.redirect(f'/my/bookings/{booking_id}?success=cancelled')

        return request.redirect(f'/my/bookings/{booking_id}?error=cannot_cancel')
