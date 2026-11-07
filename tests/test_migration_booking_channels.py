import importlib.util
import os
from datetime import timedelta

from odoo import fields
from odoo.modules.module import get_module_path
from odoo.tests import TransactionCase, new_test_user, tagged

MIGRATION = ('migrations', '18.0.1.0.3', 'post-migrate.py')
PRE_MIGRATION = ('migrations', '18.0.1.0.3', 'pre-migrate.py')


def load_migration(parts=MIGRATION):
    path = os.path.join(get_module_path('odoo_booking_reservation'), *parts)
    spec = importlib.util.spec_from_file_location(
        'booking_%s_18_0_1_0_3' % parts[-1].replace('-', '_')[:-3], path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@tagged('post_install', '-at_install', 'booking_security')
class TestMigrationBookingChannels(TransactionCase):
    """9134b70d1314: existing booking discussions (type 'channel' open to the
    portal group) become members-only groups on upgrade."""

    def test_migration_converts_booking_channels(self):
        portal_group = self.env.ref('base.group_portal')
        member = new_test_user(self.env, 'bkg_mig_member', groups='base.group_portal')
        outsider = new_test_user(self.env, 'bkg_mig_outsider', groups='base.group_portal')
        resource = self.env['booking.resource.type'].create({
            'name': 'Room Migration', 'share_type': 'all', 'slot_duration': 1.0, 'slot_interval': 1.0})
        start = fields.Datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=4)
        booking = self.env['booking.reservation'].create({
            'resource_type_id': resource.id, 'partner_id': member.partner_id.id,
            'start_datetime': start, 'end_datetime': start + timedelta(hours=1)})
        Channel = self.env['discuss.channel']
        # a channel as created by 18.0.1.0.2
        legacy = Channel.create({
            'name': '[Room Migration] legacy', 'channel_type': 'channel',
            'group_public_id': portal_group.id})
        legacy._add_members(partners=member.partner_id)
        # auto-subscription groups are not allowed on groups either (set in SQL:
        # through the ORM it would subscribe every portal user right away)
        self.env.cr.execute(
            "INSERT INTO discuss_channel_res_groups_rel (discuss_channel_id, res_groups_id) VALUES (%s, %s)",
            [legacy.id, portal_group.id])
        thread = Channel.create({'name': 'legacy thread', 'channel_type': 'channel',
                                 'parent_channel_id': legacy.id})
        booking.channel_id = legacy
        unrelated = Channel.create({'name': 'Customer News', 'channel_type': 'channel',
                                    'group_public_id': portal_group.id})
        self.env.flush_all()
        self.assertTrue(Channel.with_user(outsider).search([('id', '=', legacy.id)]),
                        'precondition: the legacy channel is open to every portal user')

        migration = load_migration()
        migration.migrate(self.env.cr, '18.0.1.0.2')
        self.env.invalidate_all()

        self.assertEqual(legacy.channel_type, 'group')
        self.assertFalse(legacy.group_public_id)
        self.assertFalse(legacy.group_ids)
        self.assertEqual(thread.channel_type, 'group')
        self.assertFalse(thread.parent_channel_id)
        self.assertEqual(unrelated.channel_type, 'channel', 'other channels are left alone')
        self.assertEqual(unrelated.group_public_id, portal_group)
        self.assertFalse(Channel.with_user(outsider).search([('id', 'in', (legacy | thread).ids)]))
        self.assertTrue(Channel.with_user(member).search([('id', '=', legacy.id)]))

        # idempotent
        self.assertEqual(migration.convert_booking_channels(self.env.cr), (0, 0))
        migration.migrate(self.env.cr, '18.0.1.0.2')
        self.env.invalidate_all()
        self.assertEqual(legacy.channel_type, 'group')


@tagged('post_install', '-at_install', 'booking_security')
class TestMigrationBookingTz(TransactionCase):
    """5289ec44235d: existing resources get the timezone their bookers were
    shown (the grid no longer follows the portal user's own timezone)."""

    def test_pre_migration_fills_booking_tz(self):
        Resource = self.env['booking.resource.type']
        booked = Resource.create({'name': 'Room Tz Booked', 'share_type': 'all',
                                  'slot_duration': 1.0, 'slot_interval': 1.0})
        idle = Resource.create({'name': 'Room Tz Idle', 'share_type': 'all',
                                'slot_duration': 1.0, 'slot_interval': 1.0})
        kept = Resource.create({'name': 'Room Tz Kept', 'share_type': 'all', 'booking_tz': 'Europe/Paris',
                                'slot_duration': 1.0, 'slot_interval': 1.0})
        tokyo = self.env['res.partner'].create([{'name': 'Tokyo %s' % i, 'tz': 'Asia/Tokyo'} for i in range(2)])
        lisbon = self.env['res.partner'].create({'name': 'Lisbon', 'tz': 'Europe/Lisbon'})
        start = fields.Datetime.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=5)
        for offset, partner in enumerate(tokyo | lisbon):
            self.env['booking.reservation'].create({
                'resource_type_id': booked.id, 'partner_id': partner.id,
                'start_datetime': start + timedelta(hours=offset),
                'end_datetime': start + timedelta(hours=offset + 1)})
        self.env.company.partner_id.tz = 'America/New_York'
        self.env.flush_all()
        # the state before the upgrade: no value (the ORM adds NOT NULL later)
        self.env.cr.execute("ALTER TABLE booking_resource_type ALTER COLUMN booking_tz DROP NOT NULL")
        self.env.cr.execute("UPDATE booking_resource_type SET booking_tz = NULL WHERE id IN %s",
                            [(booked.id, idle.id)])

        migration = load_migration(PRE_MIGRATION)
        migration.migrate(self.env.cr, '18.0.1.0.2')
        self.env.invalidate_all()
        self.assertEqual(booked.booking_tz, 'Asia/Tokyo', 'most common timezone of its bookers')
        self.assertEqual(idle.booking_tz, 'America/New_York', 'company timezone')
        self.assertEqual(kept.booking_tz, 'Europe/Paris', 'existing values are kept')
        # idempotent
        self.assertEqual(migration.fill_booking_tz(self.env.cr)[0], 0)
        self.env.cr.execute("SELECT count(*) FROM booking_resource_type WHERE booking_tz IS NULL")
        self.assertEqual(self.env.cr.fetchone()[0], 0)
