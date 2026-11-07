from datetime import datetime, time, timedelta

import pytz

from odoo.tests import new_test_user

PORTAL_TZ = 'Asia/Taipei'


def local_slot(days=1, hour=10, minute=0, duration=1.0, tz=PORTAL_TZ):
    """(start_local, end_local) naive datetimes `days` after today in `tz`."""
    today = datetime.now(pytz.UTC).astimezone(pytz.timezone(tz)).date()
    start = datetime.combine(today + timedelta(days=days), time(hour, minute))
    return start, start + timedelta(hours=duration)


def to_utc(local_dt, tz=PORTAL_TZ):
    return pytz.timezone(tz).localize(local_dt).astimezone(pytz.UTC).replace(tzinfo=None)


class BookingSecurityFixture:
    """Shared data: a bookable resource with a 08:00-20:00 grid every day,
    a portal booker working for a customer company, a colleague, an internal
    user, unrelated contacts and a second (unrelated) portal user."""

    @classmethod
    def _setup_booking_fixture(cls):
        env = cls.env
        cls.resource = env['booking.resource.type'].create({
            'name': 'Room Sec',
            'share_type': 'all',
            'slot_duration': 1.0,
            'slot_interval': 1.0,
            'advance_days': 30,
            'enable_discussion': True,
            'availability_ids': [
                (0, 0, {'dayofweek': str(day), 'hour_from': 8.0, 'hour_to': 20.0})
                for day in range(7)
            ],
        })
        cls.customer_co = env['res.partner'].create({'name': 'Customer Co', 'is_company': True})
        cls.other_co = env['res.partner'].create({'name': 'Other Co', 'is_company': True})

        cls.portal = new_test_user(
            env, 'bkg_portal', groups='base.group_portal', name='Portal Paula',
            email='paula@customer.example', tz=PORTAL_TZ)
        cls.portal.partner_id.parent_id = cls.customer_co
        cls.colleague = env['res.partner'].create({
            'name': 'Colleague Carl', 'parent_id': cls.customer_co.id,
            'email': 'carl@customer.example'})
        cls.staff = new_test_user(
            env, 'bkg_staff', groups='base.group_user', name='Staff Sam',
            email='sam@tenant.example')
        cls.foreign = env['res.partner'].create({
            'name': 'Foreign Fiona', 'parent_id': cls.other_co.id,
            'email': 'fiona@other.example'})
        # a contact of the tenant company without user (e.g. an HR work
        # contact): the old "same company" search listed it with its e-mail
        cls.work_contact = env['res.partner'].create({
            'name': 'Workcontact Wendy', 'company_id': env.company.id,
            'email': 'wendy@tenant.example'})
        cls.other_portal = new_test_user(
            env, 'bkg_other', groups='base.group_portal', name='Other Otto',
            email='otto@other.example', tz=PORTAL_TZ)
        cls.other_portal.partner_id.parent_id = cls.other_co
        cls.booking_user = new_test_user(
            env, 'bkg_buser', groups='base.group_user,odoo_booking_reservation.group_booking_user',
            name='Booking Bea', tz=PORTAL_TZ)

    def _vals(self, partner, start_local, end_local, **extra):
        vals = {
            'resource_type_id': self.resource.id,
            'partner_id': partner.id,
            'start_datetime': to_utc(start_local),
            'end_datetime': to_utc(end_local),
        }
        vals.update(extra)
        return vals
