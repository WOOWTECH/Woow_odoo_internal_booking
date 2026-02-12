from odoo import http, fields, _
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager
from odoo.exceptions import AccessError, MissingError
from datetime import datetime, timedelta
import json


class BookingPortal(CustomerPortal):
    """
    Portal Controller for Resource Booking.
    Does not depend on website module - uses portal.portal_layout template.
    """

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

    @http.route('/my/booking/resources', type='http', auth='user', website=False)
    def portal_my_resources(self, **kw):
        """Display list of resources available to the user."""
        partner = request.env.user.partner_id
        resources = self._get_accessible_resources(partner)

        values = {
            'resources': resources,
            'page_name': 'booking_resources',
        }

        return request.render('booking_reservation.portal_my_resources', values)

    # ============================================================
    # RESOURCE DETAIL & BOOKING
    # ============================================================

    @http.route('/my/booking/resources/<int:resource_id>', type='http', auth='user', website=False)
    def portal_resource_detail(self, resource_id, date=None, **kw):
        """Display resource details and available slots."""
        partner = request.env.user.partner_id
        resource = request.env['booking.resource.type'].sudo().browse(resource_id)

        if not self._check_resource_access(resource, partner):
            raise AccessError(_("You don't have access to this resource."))

        # Date range for slots
        if date:
            try:
                selected_date = datetime.strptime(date, '%Y-%m-%d').date()
            except ValueError:
                selected_date = datetime.now().date()
        else:
            selected_date = datetime.now().date()

        # Show one week of slots
        date_from = selected_date
        date_to = selected_date + timedelta(days=7)

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
            'page_name': 'booking_resource_detail',
        }

        return request.render('booking_reservation.portal_resource_detail', values)

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
            date_from = datetime.now().date()

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

    @http.route('/my/bookings/new', type='http', auth='user', website=False)
    def portal_new_booking(self, resource_id=None, **kw):
        """New booking page - select resource."""
        partner = request.env.user.partner_id
        resources = self._get_accessible_resources(partner)

        if not resources:
            return request.render('booking_reservation.portal_no_resources')

        selected_resource = None
        if resource_id:
            selected_resource = resources.filtered(lambda r: r.id == int(resource_id))

        values = {
            'resources': resources,
            'selected_resource': selected_resource[:1] if selected_resource else None,
            'page_name': 'booking_new',
        }

        return request.render('booking_reservation.portal_new_booking', values)

    @http.route('/my/bookings/create', type='http', auth='user', methods=['POST'], website=False)
    def portal_create_booking(self, **post):
        """Create a new booking."""
        partner = request.env.user.partner_id

        try:
            resource_id = int(post.get('resource_id', 0))
            start_datetime = post.get('start_datetime')
            end_datetime = post.get('end_datetime')
            note = post.get('note', '')

            if not resource_id or not start_datetime or not end_datetime:
                return request.redirect('/my/bookings/new?error=missing_fields')

            resource = request.env['booking.resource.type'].sudo().browse(resource_id)

            if not self._check_resource_access(resource, partner):
                return request.redirect('/my/bookings/new?error=unauthorized')

            # Create reservation
            reservation = request.env['booking.reservation'].sudo().create({
                'resource_type_id': resource_id,
                'start_datetime': start_datetime,
                'end_datetime': end_datetime,
                'partner_id': partner.id,
                'note': note,
                'state': 'confirmed',
            })

            return request.redirect(f'/my/bookings/{reservation.id}?success=created')

        except Exception as e:
            return request.redirect(f'/my/bookings/new?error={str(e)}')

    # ============================================================
    # MY BOOKINGS LIST
    # ============================================================

    @http.route('/my/bookings', type='http', auth='user', website=False)
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
            'date_desc': {'label': _('Date (newest)'), 'order': 'start_datetime desc'},
            'date_asc': {'label': _('Date (oldest)'), 'order': 'start_datetime asc'},
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

        return request.render('booking_reservation.portal_my_bookings', values)

    # ============================================================
    # BOOKING DETAIL
    # ============================================================

    @http.route('/my/bookings/<int:booking_id>', type='http', auth='user', website=False)
    def portal_booking_detail(self, booking_id, **kw):
        """Display booking details."""
        partner = request.env.user.partner_id
        reservation = request.env['booking.reservation'].sudo().browse(booking_id)

        if not reservation.exists() or reservation.partner_id.id != partner.id:
            raise MissingError(_("This booking does not exist or you don't have access to it."))

        success = kw.get('success')
        error = kw.get('error')

        values = {
            'reservation': reservation,
            'page_name': 'booking_detail',
            'success': success,
            'error': error,
        }

        return request.render('booking_reservation.portal_booking_detail', values)

    # ============================================================
    # CANCEL BOOKING
    # ============================================================

    @http.route('/my/bookings/<int:booking_id>/cancel', type='http', auth='user', methods=['POST'], website=False)
    def portal_cancel_booking(self, booking_id, **kw):
        """Cancel a booking."""
        partner = request.env.user.partner_id
        reservation = request.env['booking.reservation'].sudo().browse(booking_id)

        if not reservation.exists() or reservation.partner_id.id != partner.id:
            raise MissingError(_("This booking does not exist or you don't have access to it."))

        if reservation.state == 'confirmed':
            reservation.action_cancel()
            return request.redirect(f'/my/bookings/{booking_id}?success=cancelled')

        return request.redirect(f'/my/bookings/{booking_id}?error=cannot_cancel')
