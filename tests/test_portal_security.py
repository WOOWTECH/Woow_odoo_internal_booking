import json
from datetime import timedelta

from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import Request
from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger

from .common import PORTAL_TZ, BookingSecurityFixture, local_slot, to_utc


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
        # LIKE wildcards are literal characters: they cannot list everybody
        for query in ('%%', '__', '%_', '_%', '\\\\'):
            self.assertEqual(self._search(query), [], query)

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
        # core refuses sub-channels under a non-'channel' parent (a thread of a
        # group would take the parent's empty group_public_id: public)
        with self.assertRaises(UserError), mute_logger('odoo.sql_db'):
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

    def _post_confirm(self, start_local, end_local):
        return self.url_open(
            '/my/bookings/confirm?resource_id=%s&start_datetime=%s&end_datetime=%s' % (
                self.resource.id, start_local.strftime('%Y-%m-%d %H:%M:%S'),
                end_local.strftime('%Y-%m-%d %H:%M:%S')),
            allow_redirects=False)

    def test_portal_slot_must_match_to_the_second(self):
        """5289ec44235d: off-grid by seconds is off-grid (it would also block
        the next slot)."""
        start, end = local_slot(days=1, hour=10)
        cases = (
            (start, end + timedelta(seconds=59)),                          # 10:00:00 - 11:00:59
            (start + timedelta(seconds=59), end + timedelta(seconds=59)),  # 10:00:59 - 11:00:59
            (start + timedelta(seconds=1), end),                           # 10:00:01 - 11:00:00
        )
        self.authenticate('bkg_portal', 'bkg_portal')
        for case_start, case_end in cases:
            response = self._post_create(case_start, case_end)
            self.assertIn('error=invalid_slot', response.headers.get('Location', ''), case_start)
            response = self._post_confirm(case_start, case_end)
            self.assertIn('error=invalid_slot', response.headers.get('Location', ''), case_start)
        self.assertFalse(self._bookings(self.portal.partner_id))
        # model level (portal env.user, sudo like the controllers)
        Reservation = self.env['booking.reservation'].with_user(self.portal).sudo()
        start2, end2 = local_slot(days=2, hour=10)
        for case_start, case_end in (
                (start2, end2 + timedelta(seconds=59)),
                (start2 + timedelta(seconds=59), end2 + timedelta(seconds=59)),
                (start2 + timedelta(minutes=13, seconds=59), end2 + timedelta(minutes=13, seconds=59)),
                (start2, end2 + timedelta(microseconds=500000))):
            with self.assertRaises(ValidationError, msg=str(case_start)):
                Reservation.create(self._vals(self.portal.partner_id, case_start, case_end))
        # the neighbouring slot stays bookable by somebody else
        self.authenticate('bkg_other', 'bkg_other')
        next_start, next_end = local_slot(days=1, hour=11)
        self.assertIn('success=created', self._post_create(next_start, next_end).headers.get('Location', ''))

    def test_portal_timezone_cannot_move_the_grid(self):
        """5289ec44235d: res.users.tz is self-writeable; the grid is in the
        resource timezone, so changing it neither opens the closed hours nor
        shifts a slot across two real slots."""
        self.authenticate('bkg_portal', 'bkg_portal')
        _response, payload = self._jsonrpc('/web/dataset/call_kw', {
            'model': 'res.users', 'method': 'write',
            'args': [[self.portal.id], {'tz': 'Pacific/Kiritimati'}], 'kwargs': {}})
        self.assertIn('result', payload, payload)
        self.env.invalidate_all()
        self.assertEqual(self.portal.tz, 'Pacific/Kiritimati')

        # a posted 08:00 is 08:00 in the resource timezone (02:00 resource
        # time if it were read in the user's Kiritimati timezone)
        start, end = local_slot(days=1, hour=8)
        self.assertIn('success=created', self._post_create(start, end).headers.get('Location', ''))
        booking = self._bookings(self.portal.partner_id)
        self.assertEqual(len(booking), 1)
        self.assertEqual(booking.start_datetime, to_utc(start))
        self.assertEqual(booking.end_datetime, to_utc(end))

        # model level: 08:00 Kiritimati = 02:00 resource time (closed);
        # 10:00 Kolkata = 12:30 resource time (across two slots)
        Reservation = self.env['booking.reservation'].with_user(self.portal).sudo()
        for user_tz, hour in (('Pacific/Kiritimati', 8), ('Asia/Kolkata', 10)):
            self.portal.tz = user_tz
            start2, end2 = local_slot(days=3, hour=hour, tz=user_tz)
            with self.assertRaises(ValidationError, msg=user_tz):
                Reservation.create({
                    'resource_type_id': self.resource.id,
                    'partner_id': self.portal.partner_id.id,
                    'start_datetime': to_utc(start2, tz=user_tz),
                    'end_datetime': to_utc(end2, tz=user_tz),
                })

        # the slot page and the slots API show the resource grid, whatever
        # the user's timezone
        self.portal.tz = 'Pacific/Kiritimati'
        self.env.flush_all()
        _response, payload = self._jsonrpc(
            '/my/booking/resources/%s/slots' % self.resource.id, {})
        result = payload['result']
        self.assertEqual(result['tz'], PORTAL_TZ)
        self.assertTrue(result['slots'])
        self.assertEqual({slot['start'][11:16] for slot in result['slots']} - {
            '%02d:00' % hour for hour in range(8, 20)}, set())
        page = self.url_open('/my/booking/resources/%s' % self.resource.id)
        self.assertIn(PORTAL_TZ, page.text)

    # -------------------- f98eca12cddf: followers / recipients of portal mail

    def _followers(self, booking):
        self.env.invalidate_all()
        return booking.sudo().message_follower_ids.partner_id

    def _notified(self, message):
        self.env.invalidate_all()
        return self.env['mail.notification'].sudo().search(
            [('mail_message_id', 'in', message.ids)]).res_partner_id | message.sudo().partner_ids

    @mute_logger('odoo.addons.mail.models.mail_thread', 'odoo.addons.odoo_booking_reservation.models.booking_reservation')
    def test_portal_cannot_make_foreign_partners_followers_or_recipients(self):
        booking = self._create_as_portal(attendee_ids=[(6, 0, self.colleague.ids)])
        intruders = self.foreign | self.work_contact | self.other_portal.partner_id
        mine = self.env['booking.reservation'].with_user(self.portal).browse(booking.id)

        # message_subscribe: foreign partners are dropped, allowed ones kept
        mine.message_subscribe(partner_ids=intruders.ids)
        self.assertFalse(self._followers(booking) & intruders)
        mine.message_subscribe(partner_ids=(self.foreign | self.staff.partner_id).ids)
        followers = self._followers(booking)
        self.assertIn(self.staff.partner_id, followers)
        self.assertNotIn(self.foreign, followers)

        # message_post(partner_ids=...): foreign partners are not notified
        message = mine.message_post(
            body='hello', message_type='comment', subtype_xmlid='mail.mt_comment',
            partner_ids=(self.foreign | self.colleague).ids)
        notified = self._notified(message)
        self.assertIn(self.colleague, notified)
        self.assertFalse(notified & intruders)
        # autofollow cannot be used to subscribe them either
        mine.with_context(mail_post_autofollow=True).message_post(
            body='again', message_type='comment', subtype_xmlid='mail.mt_comment',
            partner_ids=self.foreign.ids)
        self.assertNotIn(self.foreign, self._followers(booking))

        # message_notify
        notification = mine.message_notify(partner_ids=self.foreign.ids, body='psst')
        self.assertFalse(self._notified(notification) & intruders)

        # portal users cannot remove the staff follower, only themselves
        with self.assertRaises(AccessError):
            mine.message_unsubscribe(partner_ids=self.staff.partner_id.ids)
        mine.message_unsubscribe(partner_ids=self.portal.partner_id.ids)
        self.assertNotIn(self.portal.partner_id, self._followers(booking))
        mine.message_subscribe(partner_ids=self.portal.partner_id.ids)
        self.assertIn(self.portal.partner_id, self._followers(booking))

        # followers cannot be written directly either
        with self.assertRaises(AccessError):
            mine.write({'message_follower_ids': [(0, 0, {
                'res_model': booking._name, 'res_id': booking.id, 'partner_id': self.foreign.id})]})

        # the same through JSON-RPC, then a portal chatter post: nobody foreign
        # is a follower, so nobody foreign is notified
        self.authenticate('bkg_portal', 'bkg_portal')
        _response, payload = self._jsonrpc('/web/dataset/call_kw', {
            'model': 'booking.reservation', 'method': 'message_subscribe',
            'args': [[booking.id]], 'kwargs': {'partner_ids': intruders.ids}})
        self.assertIn('result', payload, payload)
        _response, payload = self._jsonrpc('/web/dataset/call_kw', {
            'model': 'booking.reservation', 'method': 'message_post',
            'args': [[booking.id]], 'kwargs': {
                'body': 'rpc-marker', 'message_type': 'comment', 'subtype_xmlid': 'mail.mt_comment',
                'partner_ids': intruders.ids}})
        self.assertIn('result', payload, payload)
        self.env.invalidate_all()
        rpc_message = booking.sudo().message_ids.filtered(lambda m: 'rpc-marker' in (m.body or ''))
        self.assertEqual(len(rpc_message), 1)
        self.assertFalse(self._notified(rpc_message) & intruders)
        _response, payload = self._jsonrpc('/mail/message/post', {
            'thread_model': 'booking.reservation', 'thread_id': booking.id,
            'post_data': {'body': 'Portal chatter', 'message_type': 'comment',
                          'subtype_xmlid': 'mail.mt_comment',
                          'partner_ids': (intruders | self.staff.partner_id).ids}})
        self.assertIn('result', payload, payload)
        self.assertFalse(self._followers(booking) & intruders)
        chatter = booking.sudo().message_ids.filtered(lambda m: 'Portal chatter' in (m.body or ''))
        self.assertEqual(len(chatter), 1)
        notified = self._notified(chatter)
        self.assertFalse(notified & intruders)
        self.assertIn(self.staff.partner_id, notified, 'followers are still notified')

        # internal users keep the full mail API
        manager = new_test_user(
            self.env, 'bkg_mail_manager',
            groups='base.group_user,odoo_booking_reservation.group_booking_manager')
        booking.with_user(manager).message_subscribe(partner_ids=self.foreign.ids)
        self.assertIn(self.foreign, self._followers(booking))
