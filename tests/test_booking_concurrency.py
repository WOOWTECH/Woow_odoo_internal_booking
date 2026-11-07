from datetime import timedelta
from unittest.mock import patch

import psycopg2.errors

from odoo import SUPERUSER_ID, api, fields
from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged
from odoo.tools import mute_logger


@tagged('post_install', '-at_install', 'booking_security')
class TestBookingConcurrency(TransactionCase):
    """eb99aec03a2e: two transactions booking the same slot of the same
    resource cannot both be committed."""

    def _cleanup(self, resource_id, partner_id):
        with self.registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            bookings = env['booking.reservation'].with_context(active_test=False).search(
                [('resource_type_id', '=', resource_id)])
            events = bookings.calendar_event_id
            channels = bookings.channel_id
            env['mail.mail'].search([('model', '=', 'booking.reservation'),
                                     ('res_id', 'in', bookings.ids)]).unlink()
            env['mail.message'].search([('model', '=', 'booking.reservation'),
                                        ('res_id', 'in', bookings.ids)]).unlink()
            bookings.unlink()
            events.unlink()
            channels.unlink()
            env['booking.resource.type'].browse(resource_id).unlink()
            env['res.partner'].browse(partner_id).unlink()

    def test_concurrent_overlapping_bookings_cannot_both_commit(self):
        with self.registry.cursor() as cr0:  # committed setup, visible to both cursors
            env0 = api.Environment(cr0, SUPERUSER_ID, {})
            resource = env0['booking.resource.type'].create({
                'name': 'Room Concurrency', 'share_type': 'all',
                'slot_duration': 1.0, 'slot_interval': 1.0, 'advance_days': 30})
            partner = env0['res.partner'].create({'name': 'Concurrency Booker'})
            resource_id, partner_id = resource.id, partner.id
        self.addCleanup(self._cleanup, resource_id, partner_id)

        start = fields.Datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=3)
        vals = {
            'resource_type_id': resource_id,
            'partner_id': partner_id,
            'start_datetime': start,
            'end_datetime': start + timedelta(hours=1),
        }
        cr1 = self.registry.cursor()
        cr2 = self.registry.cursor()
        try:
            # request 2 started before request 1 commits (REPEATABLE READ snapshot)
            cr2.execute('SELECT 1')
            api.Environment(cr1, SUPERUSER_ID, {})['booking.reservation'].create(vals)
            cr1.commit()
            # request 2 must not be able to commit an overlapping booking: the
            # per-resource lock makes it fail with a serialization error, which
            # Odoo answers by retrying the request ...
            with self.assertRaises(psycopg2.errors.SerializationFailure), mute_logger('odoo.sql_db'):
                api.Environment(cr2, SUPERUSER_ID, {})['booking.reservation'].create(vals)
            cr2.rollback()
            # ... and the retry (fresh snapshot) sees the first booking
            with self.assertRaises(ValidationError):
                api.Environment(cr2, SUPERUSER_ID, {})['booking.reservation'].create(vals)
            cr2.rollback()
        finally:
            for cr in (cr1, cr2):
                cr.rollback()
                cr.close()

        # the test transaction's snapshot predates cr1's commit: count through
        # a fresh cursor
        with self.registry.cursor() as cr:
            cr.execute("SELECT count(*) FROM booking_reservation WHERE resource_type_id = %s"
                       " AND state = 'confirmed'", [resource_id])
            count = cr.fetchone()[0]
        self.assertEqual(count, 1)

    def test_overlap_check_locks_the_resource_first(self):
        resource = self.env['booking.resource.type'].create({
            'name': 'Room Lock', 'share_type': 'all', 'slot_duration': 1.0, 'slot_interval': 1.0})
        partner = self.env['res.partner'].create({'name': 'Lock Booker'})
        start = fields.Datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=3)
        Reservation = self.env['booking.reservation']
        calls = []
        original = type(Reservation)._lock_resources_for_booking

        def spy(records):
            calls.append(records.resource_type_id.ids)
            return original(records)

        with patch.object(type(Reservation), '_lock_resources_for_booking', spy):
            booking = Reservation.create({
                'resource_type_id': resource.id, 'partner_id': partner.id,
                'start_datetime': start, 'end_datetime': start + timedelta(hours=1)})
        self.assertIn([resource.id], calls)
        # cancelled bookings do not lock nor conflict
        calls.clear()
        with patch.object(type(Reservation), '_lock_resources_for_booking', spy):
            booking.action_cancel()
        self.assertFalse([ids for ids in calls if ids])
