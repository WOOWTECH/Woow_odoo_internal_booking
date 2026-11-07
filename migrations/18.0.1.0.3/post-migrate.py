"""Booking discussions become members-only conversations.

Up to 18.0.1.0.2 the discussion of a reservation was a discuss.channel of
type 'channel' with group_public_id = base.group_portal: core record rules let
every portal user read and join it through /discuss/channel/*. Convert the
channels linked from booking.reservation.channel_id to type 'group' (core
rules: members only); a group must not carry group_public_id nor auto-subscribe
groups (CHECK group_public_id_check / _constraint_group_id_channel).

Threads (sub-channels) of those channels take their visibility from the
parent's group_public_id, which a group no longer has; they are detached and
turned into members-only groups as well (keeping their members and messages).

Members who already joined a booking channel are kept: there is no record of
how they joined, so review the member lists if the old channels may have been
joined by unrelated portal users.

Idempotent: only rows that still need the change are touched.
"""
import logging

_logger = logging.getLogger(__name__)


def convert_booking_channels(cr):
    cr.execute("""
        SELECT DISTINCT channel_id FROM booking_reservation
         WHERE channel_id IS NOT NULL
    """)
    booking_channel_ids = tuple(row[0] for row in cr.fetchall())
    if not booking_channel_ids:
        return 0, 0

    # threads of booking channels: detach and make them members-only too
    cr.execute("""
        UPDATE discuss_channel
           SET channel_type = 'group', group_public_id = NULL,
               parent_channel_id = NULL, from_message_id = NULL
         WHERE parent_channel_id IN %s
     RETURNING id
    """, [booking_channel_ids])
    thread_ids = tuple(row[0] for row in cr.fetchall())

    cr.execute("""
        UPDATE discuss_channel
           SET channel_type = 'group', group_public_id = NULL
         WHERE id IN %s
           AND (channel_type = 'channel' OR group_public_id IS NOT NULL)
     RETURNING id
    """, [booking_channel_ids])
    converted_ids = tuple(row[0] for row in cr.fetchall())

    touched = converted_ids + thread_ids
    if touched:
        cr.execute("""
            DELETE FROM discuss_channel_res_groups_rel
             WHERE discuss_channel_id IN %s
        """, [touched])
    return len(converted_ids), len(thread_ids)


def report_unrelated_portal_members(cr):
    """Log (do not remove) portal members of booking channels who are neither
    booker, organizer nor attendee of the reservation."""
    cr.execute("""
        SELECT r.channel_id, m.partner_id
          FROM booking_reservation r
          JOIN discuss_channel_member m ON m.channel_id = r.channel_id
          JOIN res_users u ON u.partner_id = m.partner_id AND u.share
         WHERE r.channel_id IS NOT NULL
           AND m.partner_id IS DISTINCT FROM r.partner_id
           AND m.partner_id IS DISTINCT FROM r.organizer_id
           AND NOT EXISTS (
                SELECT 1 FROM booking_reservation_attendee_rel a
                 WHERE a.reservation_id = r.id AND a.partner_id = m.partner_id)
    """)
    rows = cr.fetchall()
    if rows:
        _logger.warning(
            'odoo_booking_reservation: %s portal member(s) of booking discussions are not '
            'booker/organizer/attendee of the reservation (channel_id, partner_id): %s',
            len(rows), rows[:200])
    return rows


def migrate(cr, version):
    if not version:
        return
    converted, threads = convert_booking_channels(cr)
    _logger.info(
        'odoo_booking_reservation: %s booking discussion channel(s) converted to '
        'members-only groups, %s thread(s) detached', converted, threads)
    report_unrelated_portal_members(cr)
