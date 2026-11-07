import json

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import Request
from odoo.tests import HttpCase, tagged

from .common import BookingSecurityFixture, local_slot


@tagged('post_install', '-at_install', 'booking_security')
class TestBookingPortalSecurity(BookingSecurityFixture, HttpCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_booking_fixture()

    # ------------------------------------------------------------ helpers

    def _jsonrpc(self, route, params):
        response = self.url_open(
            route,
            data=json.dumps({'jsonrpc': '2.0', 'method': 'call', 'id': 1, 'params': params}),
            headers={'Content-Type': 'application/json'},
        )
        try:
            payload = response.json()
        except ValueError:
            payload = {}
        return response, payload

    def _search(self, query):
        response, payload = self._jsonrpc('/my/booking/attendees/search', {'query': query})
        self.assertEqual(response.status_code, 200)
        self.assertIn('result', payload, payload)
        return payload['result']['attendees']

    def _post_create(self, start_local, end_local, attendees=None, discussion=False, subject='Sec meeting'):
        data = {
            'resource_id': self.resource.id,
            'start_datetime': start_local.strftime('%Y-%m-%d %H:%M:%S'),
            'end_datetime': end_local.strftime('%Y-%m-%d %H:%M:%S'),
            'subject': subject,
            'csrf_token': Request.csrf_token(self),
        }
        if attendees is not None:
            data['attendee_ids'] = ','.join(str(p.id) for p in attendees)
        if discussion:
            data['enable_discussion'] = 'on'
        return self.url_open('/my/bookings/create', data=data, allow_redirects=False)

    def _bookings(self, partner):
        self.env.invalidate_all()
        return self.env['booking.reservation'].search(
            [('partner_id', '=', partner.id), ('resource_type_id', '=', self.resource.id)])

    def _create_as_portal(self, **extra):
        """Booking of the portal user through the portal flow (sudo, env.user=portal)."""
        start, end = local_slot(days=2, hour=extra.pop('hour', 9))
        return self.env['booking.reservation'].with_user(self.portal).sudo().create(
            self._vals(self.portal.partner_id, start, end, **extra))

    # --------------------------------------- 4618e9a17af3: attendee search

    def test_attendee_search_names_only_and_allowed_contacts_only(self):
        self.authenticate('bkg_portal', 'bkg_portal')
        # no e-mail anywhere in the payload, whatever the query
        for query in ('Staff Sam', 'Co', 'Sa', 'ex', 'example', 'Workcontact', 'Other'):
            for attendee in self._search(query):
                self.assertEqual(set(attendee), {'id', 'name'}, 'no e-mail in the result')
        # unrelated contacts and portal users of other companies are not offered
        self.assertEqual(self._search('Workcontact Wendy'), [])
        self.assertEqual(self._search('Other Otto'), [])
        self.assertEqual(self._search('Foreign Fiona'), [])
        # internal users and colleagues of the booker's company are
        staff = self._search('Staff Sam')
        self.assertEqual([a['id'] for a in staff], [self.staff.partner_id.id])
        colleague = self._search('Colleague Carl')
        self.assertEqual([a['id'] for a in colleague], [self.colleague.id])
        # the booker is never offered, queries need at least 2 characters
        self.assertEqual(self._search('Portal Paula'), [])
        self.assertEqual(self._search('S'), [])
        self.assertEqual(self._search(''), [])

    # ------------------------------------ f98eca12cddf: attendee injection

    def test_create_keeps_only_allowed_attendees(self):
        self.authenticate('bkg_portal', 'bkg_portal')
        start, end = local_slot(days=1, hour=10)
        response = self._post_create(
            start, end, discussion=True,
            attendees=self.colleague | self.staff.partner_id | self.foreign
            | self.work_contact | self.other_portal.partner_id)
        self.assertEqual(response.status_code, 303, response.text[:300])
        self.assertIn('success=created', response.headers.get('Location', ''))
        booking = self._bookings(self.portal.partner_id)
        self.assertEqual(len(booking), 1)
        self.assertEqual(booking.attendee_ids, self.colleague | self.staff.partner_id)
        intruders = self.foreign | self.work_contact | self.other_portal.partner_id
        self.assertFalse(booking.calendar_event_id.partner_ids & intruders,
                         'no calendar invitation to foreign partners')
        self.assertTrue(booking.channel_id)
        self.assertFalse(booking.channel_id.channel_member_ids.partner_id & intruders,
                         'foreign partners are not added to the discussion')
        page = self.url_open('/my/bookings/%s' % booking.id)
        self.assertEqual(page.status_code, 200)
        self.assertIn('Colleague Carl', page.text)
        self.assertNotIn('Foreign Fiona', page.text)
        self.assertNotIn('Workcontact Wendy', page.text)

    def test_portal_cannot_set_foreign_attendees_at_model_level(self):
        booking = self._create_as_portal(attendee_ids=[(6, 0, self.colleague.ids)])
        # even through sudo (portal controllers) env.user stays the portal user
        with self.assertRaises(ValidationError):
            booking.with_user(self.portal).sudo().write({'attendee_ids': [(4, self.foreign.id)]})
        with self.assertRaises(ValidationError):
            self._create_as_portal(hour=11, attendee_ids=[(6, 0, self.foreign.ids)])
        # an internal user may still invite anybody from the backend
        booking.with_user(self.booking_user).sudo().write({'attendee_ids': [(4, self.foreign.id)]})
        self.assertIn(self.foreign, booking.attendee_ids)

    def test_portal_call_kw_cannot_create_or_modify_bookings(self):
        booking = self._create_as_portal()
        Reservation = self.env['booking.reservation'].with_user(self.portal)
        with self.assertRaises(AccessError):
            Reservation.browse(booking.id).write({'attendee_ids': [(4, self.foreign.id)]})
        for vals in ({'state': 'cancelled'}, {'partner_id': self.other_portal.partner_id.id},
                     {'organizer_id': self.foreign.id}, {'enable_discussion': True},
                     {'calendar_event_id': False}, {'channel_id': False}):
            with self.assertRaises(AccessError, msg=str(vals)):
                Reservation.browse(booking.id).write(vals)
        start, end = local_slot(days=3, hour=10)
        with self.assertRaises(AccessError):
            Reservation.create(self._vals(self.portal.partner_id, start, end))
        # the same through JSON-RPC
        self.authenticate('bkg_portal', 'bkg_portal')
        _response, payload = self._jsonrpc('/web/dataset/call_kw', {
            'model': 'booking.reservation', 'method': 'write',
            'args': [[booking.id], {'attendee_ids': [[4, self.foreign.id]]}], 'kwargs': {}})
        self.assertIn('error', payload)
        self.env.invalidate_all()
        self.assertNotIn(self.foreign, booking.attendee_ids)

    def test_portal_chatter_and_cancel_still_work(self):
        booking = self._create_as_portal()
        self.authenticate('bkg_portal', 'bkg_portal')
        _response, payload = self._jsonrpc('/mail/message/post', {
            'thread_model': 'booking.reservation', 'thread_id': booking.id,
            'post_data': {'body': 'Portal hello', 'message_type': 'comment',
                          'subtype_xmlid': 'mail.mt_comment'}})
        self.assertIn('result', payload, payload)
        self.env.invalidate_all()
        self.assertIn('Portal hello', ''.join(booking.message_ids.mapped('body')))
        response = self.url_open('/my/bookings/%s/cancel' % booking.id,
                                 data={'csrf_token': Request.csrf_token(self)}, allow_redirects=False)
        self.assertIn('success=cancelled', response.headers.get('Location', ''))
        self.env.invalidate_all()
        self.assertEqual(booking.state, 'cancelled')

    # ----------------------------------- 9134b70d1314: discussion channel

    def test_booking_discussion_is_members_only(self):
        self.authenticate('bkg_portal', 'bkg_portal')
        start, end = local_slot(days=1, hour=13)
        self._post_create(start, end, discussion=True, attendees=self.staff.partner_id)
        booking = self._bookings(self.portal.partner_id)
        channel = booking.channel_id
        self.assertTrue(channel)
        channel.sudo().message_post(
            body='Secret agenda', message_type='comment', subtype_xmlid='mail.mt_comment',
            author_id=self.staff.partner_id.id)

        # an unrelated portal user cannot open, read or join it
        self.authenticate('bkg_other', 'bkg_other')
        self.assertEqual(self.url_open('/discuss/channel/%s' % channel.id).status_code, 404)
        response, payload = self._jsonrpc('/discuss/channel/messages', {'channel_id': channel.id})
        self.assertNotIn('result', payload)
        self.assertNotIn('Secret agenda', response.text)
        _response, payload = self._jsonrpc('/discuss/channel/info', {'channel_id': channel.id})
        self.assertFalse(payload.get('result'))
        _response, payload = self._jsonrpc('/discuss/channel/join', {'channel_id': channel.id})
        self.assertNotIn('result', payload)
        self.env.invalidate_all()
        self.assertNotIn(self.other_portal.partner_id, channel.channel_member_ids.partner_id)
        self.assertFalse(self.env['discuss.channel'].with_user(self.other_portal).search(
            [('id', '=', channel.id)]))
        self.assertNotIn('/discuss/channel/%s?' % channel.id, self.url_open('/my/discussions').text)

        # members: the booker opens it and sees it in /my/discussions
        self.authenticate('bkg_portal', 'bkg_portal')
        self.assertEqual(self.url_open('/discuss/channel/%s' % channel.id).status_code, 200)
        _response, payload = self._jsonrpc('/discuss/channel/messages', {'channel_id': channel.id})
        self.assertIn('Secret agenda', json.dumps(payload.get('result', {})))
        listing = self.url_open('/my/discussions').text
        self.assertIn('/discuss/channel/%s?discussions=1' % channel.id, listing)
        redirect = self.url_open('/my/bookings/%s/discuss' % booking.id, allow_redirects=False)
        self.assertIn('open_channel=%s' % channel.id, redirect.headers.get('Location', ''))
        self.assertIn('/discuss/channel/%s?discussions=1' % channel.id,
                      self.url_open('/my/discussions?open_channel=%s' % channel.id).text)

        self.assertEqual(channel.channel_type, 'group')
        self.assertFalse(channel.group_public_id)
        self.assertEqual(channel.channel_member_ids.partner_id,
                         self.portal.partner_id | self.staff.partner_id)

    def test_no_threads_in_booking_discussions(self):
        booking = self._create_as_portal(enable_discussion=True)
        channel = booking.channel_id
        self.assertEqual(channel.channel_type, 'group')
        channel._add_members(partners=self.staff.partner_id)
        with self.assertRaises(UserError):
            channel.with_user(self.staff)._create_sub_channel(name='side thread')
        # other channels keep their threads
        other = self.env['discuss.channel'].create({'name': 'Plain', 'channel_type': 'channel'})
        self.assertTrue(other._create_sub_channel(name='ok'))

    # ------------------------------ 5289ec44235d: availability / slot grid

    def test_off_grid_booking_rejected_for_portal(self):
        self.authenticate('bkg_portal', 'bkg_portal')
        for start, end in (local_slot(days=1, hour=10, minute=30),   # between two slots
                           local_slot(days=1, hour=22),              # outside availability
                           local_slot(days=1, hour=5)):
            response = self._post_create(start, end)
            self.assertIn('error=invalid_slot', response.headers.get('Location', ''), start)
        self.assertFalse(self._bookings(self.portal.partner_id))
        # the confirmation page refuses it too
        start, end = local_slot(days=1, hour=10, minute=30)
        response = self.url_open('/my/bookings/confirm?resource_id=%s&start_datetime=%s&end_datetime=%s' % (
            self.resource.id, start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')),
            allow_redirects=False)
        self.assertIn('error=invalid_slot', response.headers.get('Location', ''))
        # model level (portal env.user even under sudo)
        start, end = local_slot(days=2, hour=10, minute=30)
        with self.assertRaises(ValidationError):
            self.env['booking.reservation'].with_user(self.portal).sudo().create(
                self._vals(self.portal.partner_id, start, end))
        # an offered slot works
        start, end = local_slot(days=1, hour=10)
        page = self.url_open('/my/bookings/confirm?resource_id=%s&start_datetime=%s&end_datetime=%s' % (
            self.resource.id, start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')))
        self.assertEqual(page.status_code, 200)
        self.assertIn('id="attendee_search"', page.text)
        response = self._post_create(start, end)
        self.assertIn('success=created', response.headers.get('Location', ''))
        self.assertEqual(len(self._bookings(self.portal.partner_id)), 1)

    def test_backend_users_keep_free_scheduling(self):
        start, end = local_slot(days=2, hour=22, minute=15)
        booking = self.env['booking.reservation'].with_user(self.booking_user).create(
            self._vals(self.booking_user.partner_id, start, end))
        self.assertEqual(booking.state, 'confirmed')

    # ---------------------------------------------- eb99aec03a2e: overlap

    def test_rejected_overlap_is_not_persisted(self):
        start, end = local_slot(days=1, hour=15)
        self.authenticate('bkg_portal', 'bkg_portal')
        self.assertIn('success=created', self._post_create(start, end).headers.get('Location', ''))
        self.authenticate('bkg_other', 'bkg_other')
        response = self._post_create(start, end)
        self.assertIn('error=slot_taken', response.headers.get('Location', ''))
        self.env.invalidate_all()
        confirmed = self.env['booking.reservation'].search([
            ('resource_type_id', '=', self.resource.id), ('state', '=', 'confirmed')])
        self.assertEqual(confirmed.partner_id, self.portal.partner_id,
                         'the refused booking must not be committed with the request')
