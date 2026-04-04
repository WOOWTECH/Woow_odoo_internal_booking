from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
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
        """
        slots = resource._generate_slots(date_from, date_to)

        # Get existing reservations for this period
        reservations = request.env['booking.reservation'].sudo().search([
            ('resource_type_id', '=', resource.id),
            ('state', '=', 'confirmed'),
            ('start_datetime', '>=', datetime.combine(date_from, datetime.min.time())),
            ('end_datetime', '<=', datetime.combine(date_to, datetime.max.time())),
        ])

        # Mark slot availability
        for slot in slots:
            slot['is_available'] = True
            slot['is_mine'] = False
            slot['reservation_id'] = False

            for res in reservations:
                res_start = fields.Datetime.to_datetime(res.start_datetime)
                res_end = fields.Datetime.to_datetime(res.end_datetime)

                # Check overlap
                if slot['start'] < res_end and slot['end'] > res_start:
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
    # RESOURCE DETAIL & BOOKING
    # ============================================================

    @http.route('/my/booking/resources/<int:resource_id>', type='http', auth='user', website=True)
    def portal_resource_detail(self, resource_id, date=None, **kw):
        """Display resource details and available slots."""
        partner = request.env.user.partner_id
        resource = request.env['booking.resource.type'].sudo().browse(resource_id)

        if not self._check_resource_access(resource, partner):
            raise AccessError(_("您沒有存取此資源的權限。"))

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
            'date_from_str': date_from.strftime('%m/%d'),
            'date_to_str': date_to.strftime('%Y/%m/%d'),
            'prev_week': max(today, date_from - timedelta(days=7)).strftime('%Y-%m-%d'),
            'next_week': min(max_date, date_from + timedelta(days=7)).strftime('%Y-%m-%d'),
            'show_prev': date_from > today,
            'show_next': date_from + timedelta(days=7) < max_date,
            'page_name': 'booking_resource_detail',
        }

        return request.render('odoo_booking_reservation.portal_resource_detail', values)

    @http.route('/my/booking/resources/<int:resource_id>/slots', type='json', auth='user')
    def portal_get_slots(self, resource_id, date_from=None, date_to=None, **kw):
        """API: Get available slots for a resource (JSON)."""
        partner = request.env.user.partner_id
        resource = request.env['booking.resource.type'].sudo().browse(resource_id)

        if not self._check_resource_access(resource, partner):
            return {'error': 'Unauthorized'}

        if date_from:
            date_from = datetime.strptime(date_from, '%Y-%m-%d').date()
        else:
            date_from = self._get_local_now().date()

        if date_to:
            date_to = datetime.strptime(date_to, '%Y-%m-%d').date()
        else:
            date_to = date_from + timedelta(days=resource.advance_days)

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

            # Build reservation vals
            vals = {
                'resource_type_id': resource_id,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'partner_id': partner.id,
                'organizer_id': partner.id,
                'state': 'confirmed',
            }

            if subject:
                vals['subject'] = subject
            if description:
                vals['description'] = description
            if enable_discussion and resource.enable_discussion:
                vals['enable_discussion'] = True

            # Create reservation
            reservation = request.env['booking.reservation'].sudo().create(vals)

            return request.redirect(f'/my/bookings/{reservation.id}?success=created')

        except Exception as e:
            return request.redirect(f'/my/bookings/new?error={str(e)}')

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
            'all': {'label': '全部', 'domain': []},
            'upcoming': {'label': '即將到來', 'domain': [('start_datetime', '>=', fields.Datetime.now()), ('state', '=', 'confirmed')]},
            'past': {'label': '已過期', 'domain': [('start_datetime', '<', fields.Datetime.now())]},
            'confirmed': {'label': '已確認', 'domain': [('state', '=', 'confirmed')]},
            'cancelled': {'label': '已取消', 'domain': [('state', '=', 'cancelled')]},
        }

        if filterby not in filter_options:
            filterby = 'upcoming'

        domain += filter_options[filterby]['domain']

        # Sort options
        sort_options = {
            'date_desc': {'label': '日期（最新）', 'order': 'start_datetime desc'},
            'date_asc': {'label': '日期（最舊）', 'order': 'start_datetime asc'},
            'resource': {'label': '資源', 'order': 'resource_type_id, start_datetime desc'},
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
            raise MissingError(_("此預定不存在或您無權存取。"))

        success = kw.get('success')
        error = kw.get('error')

        values = {
            'reservation': reservation,
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

        # Portal users cannot access /odoo/discuss (backend-only route)
        # Use portal-friendly route from cs_portal_discuss module instead
        if request.env.user.has_group('base.group_user'):
            return request.redirect('/odoo/action-mail.action_discuss?active_id=discuss.channel_%s' % reservation.channel_id.id)
        else:
            return request.redirect('/discuss/channel/%s?discussions=1' % reservation.channel_id.id)

    # ============================================================
    # CANCEL BOOKING
    # ============================================================

    @http.route('/my/bookings/<int:booking_id>/cancel', type='http', auth='user', methods=['POST'], website=True)
    def portal_cancel_booking(self, booking_id, **kw):
        """Cancel a booking."""
        partner = request.env.user.partner_id
        reservation = request.env['booking.reservation'].sudo().browse(booking_id)

        if not reservation.exists() or reservation.partner_id.id != partner.id:
            raise MissingError(_("此預定不存在或您無權存取。"))

        if reservation.state == 'confirmed':
            reservation.action_cancel()
            return request.redirect(f'/my/bookings/{booking_id}?success=cancelled')

        return request.redirect(f'/my/bookings/{booking_id}?error=cannot_cancel')
