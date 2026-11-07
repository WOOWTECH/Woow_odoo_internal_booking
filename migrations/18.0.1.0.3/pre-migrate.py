"""Resources get their own timezone (booking.resource.type.booking_tz).

Up to 18.0.1.0.2 the portal built the slot grid in the timezone of the user
looking at it. Portal users can change their own timezone (res.users.tz is
self-writeable), which let them move the grid outside the availability or
across two slots. From 18.0.1.0.3 the grid is in the resource timezone.

The column is created here, before the ORM adds it, so that existing resources
keep the grid their bookers were shown, rather than the timezone of whoever runs
the upgrade:

1. the most common timezone of the resource's bookers;
2. otherwise the timezone of the main company's partner;
3. otherwise the timezone of the administrator (base.user_admin);
4. otherwise UTC.

Idempotent: only resources without a timezone are filled.
"""
import logging

_logger = logging.getLogger(__name__)


def fill_booking_tz(cr):
    """Fill booking_tz where it is empty; return (rows set, default timezone)."""
    cr.execute("ALTER TABLE booking_resource_type ADD COLUMN IF NOT EXISTS booking_tz varchar")

    cr.execute("""
        UPDATE booking_resource_type t
           SET booking_tz = best.tz
          FROM (
                SELECT DISTINCT ON (r.resource_type_id) r.resource_type_id AS resource_id, p.tz
                  FROM booking_reservation r
                  JOIN res_partner p ON p.id = r.partner_id
                 WHERE COALESCE(p.tz, '') != ''
              GROUP BY r.resource_type_id, p.tz
              ORDER BY r.resource_type_id, count(*) DESC, p.tz
               ) best
         WHERE t.id = best.resource_id
           AND COALESCE(t.booking_tz, '') = ''
    """)
    filled = cr.rowcount

    cr.execute("""
        SELECT p.tz
          FROM res_company c
          JOIN res_partner p ON p.id = c.partner_id
         WHERE COALESCE(p.tz, '') != ''
      ORDER BY c.id
         LIMIT 1
    """)
    row = cr.fetchone()
    if not row:
        cr.execute("""
            SELECT p.tz
              FROM ir_model_data d
              JOIN res_users u ON u.id = d.res_id
              JOIN res_partner p ON p.id = u.partner_id
             WHERE d.module = 'base' AND d.name = 'user_admin' AND d.model = 'res.users'
               AND COALESCE(p.tz, '') != ''
        """)
        row = cr.fetchone()
    default_tz = row[0] if row else 'UTC'

    cr.execute("""
        UPDATE booking_resource_type
           SET booking_tz = %s
         WHERE COALESCE(booking_tz, '') = ''
    """, [default_tz])
    return filled + cr.rowcount, default_tz


def migrate(cr, version):
    if not version:
        return
    count, default_tz = fill_booking_tz(cr)
    _logger.info(
        'odoo_booking_reservation: timezone set on %s booking resource(s) (default %s)',
        count, default_tz)
