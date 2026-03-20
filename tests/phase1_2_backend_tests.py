#!/usr/bin/env python3
"""
Phase 1 & 2: Backend CRUD and Permission Tests for Odoo Booking Reservation module.

Phase 1: Manager tests (test_manager) - full CRUD on all models.
Phase 2: User permission tests (test_user) - verify access restrictions.

Run from project root:
    python3 tests/phase1_2_backend_tests.py
"""
import sys
import json
import traceback
import xmlrpc.client

sys.path.insert(0, '.')
from tests.odoo_rpc import OdooRPC


def is_access_error(exc):
    """Detect an Odoo AccessError from an XML-RPC Fault.

    Odoo maps AccessError to Fault code 4. The message may be in any
    language (this instance uses Traditional Chinese), so we check the
    fault code first, then fall back to keyword matching.
    """
    if isinstance(exc, xmlrpc.client.Fault):
        if exc.faultCode == 4:
            return True
    msg = str(exc).lower()
    return 'accesserror' in msg or 'access' in msg or 'not allowed' in msg


def call_action(rpc, model, method, record_ids):
    """Call an Odoo action method that may return None.

    Odoo action methods (action_cancel, action_confirm, ...) typically
    return None. The server-side OdooMarshaller does NOT allow_none,
    so it raises a TypeError Fault (code 1) when trying to serialize
    the None return value. The action itself has already executed
    successfully on the server. We catch that specific fault and treat
    it as success.
    """
    try:
        rpc.execute(model, method, record_ids)
    except xmlrpc.client.Fault as f:
        if f.faultCode == 1 and 'cannot marshal None' in str(f):
            # Action executed OK; the None return value just can't be
            # serialized by Odoo's XML-RPC marshaller.
            return True
        raise
    return True

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
with open('tests/test_config.json') as f:
    CONFIG = json.load(f)

RESOURCE_CONF_A = CONFIG['resources']['Conference Room A']
CATEGORY_MEETING = CONFIG['categories']['Meeting Rooms']
CATEGORY_EQUIPMENT = CONFIG['categories']['Equipment']

# ---------------------------------------------------------------------------
# Test harness
# ---------------------------------------------------------------------------
results = []  # list of (phase, name, passed, detail)


def record(phase, name, passed, detail=""):
    tag = "PASS" if passed else "FAIL"
    results.append((phase, name, passed, detail))
    print(f"  [{tag}] {name}" + (f"  -- {detail}" if detail else ""))


def section(title):
    print(f"\n{'=' * 64}")
    print(f"  {title}")
    print(f"{'=' * 64}")


# ===================================================================
# PHASE 1: Manager Tests
# ===================================================================
section("PHASE 1: Manager CRUD Tests (test_manager)")

mgr = OdooRPC("test_manager", "test_manager")
print(f"  Authenticated as test_manager (uid={mgr.uid})")

# Track IDs to clean up
cleanup_ids = {
    'booking.resource.category': [],
    'booking.resource.type': [],
    'booking.reservation': [],
    'booking.resource.availability': [],
}

# ------------------------------------------------------------------
# 1.1  Category CRUD
# ------------------------------------------------------------------
print("\n--- 1.1 Category CRUD ---")

# CREATE
try:
    cat_id = mgr.create('booking.resource.category', {
        'name': 'Test Category Phase1',
        'sequence': 99,
    })
    cleanup_ids['booking.resource.category'].append(cat_id)
    record("P1", "Category CREATE", bool(cat_id), f"id={cat_id}")
except Exception as e:
    record("P1", "Category CREATE", False, str(e))
    cat_id = None

# READ
try:
    if cat_id:
        data = mgr.read('booking.resource.category', [cat_id],
                         fields=['name', 'sequence', 'active'])
        ok = data and data[0]['name'] == 'Test Category Phase1'
        record("P1", "Category READ", ok, f"name={data[0]['name']}" if data else "no data")
    else:
        record("P1", "Category READ", False, "skipped, no cat_id")
except Exception as e:
    record("P1", "Category READ", False, str(e))

# UPDATE
try:
    if cat_id:
        mgr.write('booking.resource.category', [cat_id], {'name': 'Test Category Renamed'})
        data = mgr.read('booking.resource.category', [cat_id], fields=['name'])
        ok = data and data[0]['name'] == 'Test Category Renamed'
        record("P1", "Category UPDATE name", ok, f"name={data[0]['name']}" if data else "")
    else:
        record("P1", "Category UPDATE name", False, "skipped")
except Exception as e:
    record("P1", "Category UPDATE name", False, str(e))

# DELETE
try:
    if cat_id:
        mgr.unlink('booking.resource.category', [cat_id])
        remaining = mgr.search('booking.resource.category', [('id', '=', cat_id)])
        ok = len(remaining) == 0
        record("P1", "Category DELETE", ok, "deleted" if ok else f"still found {remaining}")
        if ok:
            cleanup_ids['booking.resource.category'].remove(cat_id)
    else:
        record("P1", "Category DELETE", False, "skipped")
except Exception as e:
    record("P1", "Category DELETE", False, str(e))

# ------------------------------------------------------------------
# 1.2  Resource Type CRUD
# ------------------------------------------------------------------
print("\n--- 1.2 Resource Type CRUD ---")

# CREATE with all fields
try:
    rt_id = mgr.create('booking.resource.type', {
        'name': 'Test Room Phase1',
        'description': 'A room created by the test suite',
        'sequence': 50,
        'location': 'Test Building, Floor 0',
        'capacity': 12,
        'slot_duration': 1.0,
        'slot_interval': 1.0,
        'advance_days': 14,
        'share_type': 'all',
        'category_id': CATEGORY_MEETING,
    })
    cleanup_ids['booking.resource.type'].append(rt_id)
    record("P1", "Resource Type CREATE", bool(rt_id), f"id={rt_id}")
except Exception as e:
    record("P1", "Resource Type CREATE", False, str(e))
    rt_id = None

# READ
try:
    if rt_id:
        data = mgr.read('booking.resource.type', [rt_id],
                         fields=['name', 'location', 'capacity', 'slot_duration',
                                 'share_type', 'category_id', 'active'])
        d = data[0] if data else {}
        ok = d.get('name') == 'Test Room Phase1' and d.get('capacity') == 12
        record("P1", "Resource Type READ", ok,
               f"name={d.get('name')}, cap={d.get('capacity')}, loc={d.get('location')}")
    else:
        record("P1", "Resource Type READ", False, "skipped")
except Exception as e:
    record("P1", "Resource Type READ", False, str(e))

# UPDATE settings
try:
    if rt_id:
        mgr.write('booking.resource.type', [rt_id], {
            'capacity': 20,
            'slot_duration': 2.0,
            'location': 'Updated Building, Floor 1',
        })
        data = mgr.read('booking.resource.type', [rt_id],
                         fields=['capacity', 'slot_duration', 'location'])
        d = data[0] if data else {}
        ok = d.get('capacity') == 20 and d.get('slot_duration') == 2.0
        record("P1", "Resource Type UPDATE settings", ok,
               f"cap={d.get('capacity')}, slot={d.get('slot_duration')}, loc={d.get('location')}")
    else:
        record("P1", "Resource Type UPDATE settings", False, "skipped")
except Exception as e:
    record("P1", "Resource Type UPDATE settings", False, str(e))

# ARCHIVE / UNARCHIVE
try:
    if rt_id:
        mgr.write('booking.resource.type', [rt_id], {'active': False})
        data = mgr.read('booking.resource.type', [rt_id], fields=['active'])
        archived = data and data[0]['active'] is False
        record("P1", "Resource Type ARCHIVE", archived, f"active={data[0]['active']}" if data else "")

        mgr.write('booking.resource.type', [rt_id], {'active': True})
        data = mgr.read('booking.resource.type', [rt_id], fields=['active'])
        unarchived = data and data[0]['active'] is True
        record("P1", "Resource Type UNARCHIVE", unarchived, f"active={data[0]['active']}" if data else "")
    else:
        record("P1", "Resource Type ARCHIVE", False, "skipped")
        record("P1", "Resource Type UNARCHIVE", False, "skipped")
except Exception as e:
    record("P1", "Resource Type ARCHIVE/UNARCHIVE", False, str(e))

# DELETE
try:
    if rt_id:
        mgr.unlink('booking.resource.type', [rt_id])
        remaining = mgr.search('booking.resource.type', [('id', '=', rt_id)])
        ok = len(remaining) == 0
        record("P1", "Resource Type DELETE", ok, "deleted" if ok else f"still found {remaining}")
        if ok:
            cleanup_ids['booking.resource.type'].remove(rt_id)
    else:
        record("P1", "Resource Type DELETE", False, "skipped")
except Exception as e:
    record("P1", "Resource Type DELETE", False, str(e))

# ------------------------------------------------------------------
# 1.3  Reservation CRUD
# ------------------------------------------------------------------
print("\n--- 1.3 Reservation CRUD ---")

# We need a resource type and partner for the reservation.
# Use Conference Room A from config, and the manager's own partner.
mgr_partner = mgr.read('res.users', [mgr.uid], fields=['partner_id'])[0]['partner_id'][0]
res_type_id = RESOURCE_CONF_A['id']

# CREATE reservation
try:
    rv_id = mgr.create('booking.reservation', {
        'resource_type_id': res_type_id,
        'start_datetime': '2026-03-25 10:00:00',
        'end_datetime': '2026-03-25 11:00:00',
        'partner_id': mgr_partner,
        'note': 'Phase 1 test reservation',
    })
    cleanup_ids['booking.reservation'].append(rv_id)
    record("P1", "Reservation CREATE", bool(rv_id), f"id={rv_id}")
except Exception as e:
    record("P1", "Reservation CREATE", False, str(e))
    rv_id = None

# READ
try:
    if rv_id:
        data = mgr.read('booking.reservation', [rv_id],
                         fields=['name', 'resource_type_id', 'start_datetime', 'end_datetime',
                                 'duration', 'partner_id', 'state', 'note'])
        d = data[0] if data else {}
        ok = bool(d.get('resource_type_id')) and d.get('state') == 'confirmed'
        record("P1", "Reservation READ", ok,
               f"name={d.get('name')}, state={d.get('state')}, duration={d.get('duration')}")
    else:
        record("P1", "Reservation READ", False, "skipped")
except Exception as e:
    record("P1", "Reservation READ", False, str(e))

# UPDATE
try:
    if rv_id:
        mgr.write('booking.reservation', [rv_id], {
            'note': 'Updated note from phase 1',
            'end_datetime': '2026-03-25 12:00:00',
        })
        data = mgr.read('booking.reservation', [rv_id],
                         fields=['note', 'end_datetime', 'duration'])
        d = data[0] if data else {}
        ok = d.get('note') == 'Updated note from phase 1'
        record("P1", "Reservation UPDATE", ok,
               f"note={d.get('note')}, end={d.get('end_datetime')}, dur={d.get('duration')}")
    else:
        record("P1", "Reservation UPDATE", False, "skipped")
except Exception as e:
    record("P1", "Reservation UPDATE", False, str(e))

# CANCEL via action_cancel
try:
    if rv_id:
        call_action(mgr, 'booking.reservation', 'action_cancel', [rv_id])
        data = mgr.read('booking.reservation', [rv_id], fields=['state'])
        ok = data and data[0]['state'] == 'cancelled'
        record("P1", "Reservation action_cancel", ok,
               f"state={data[0]['state']}" if data else "")
    else:
        record("P1", "Reservation action_cancel", False, "skipped")
except Exception as e:
    record("P1", "Reservation action_cancel", False, str(e))

# RE-CONFIRM via action_confirm
try:
    if rv_id:
        call_action(mgr, 'booking.reservation', 'action_confirm', [rv_id])
        data = mgr.read('booking.reservation', [rv_id], fields=['state'])
        ok = data and data[0]['state'] == 'confirmed'
        record("P1", "Reservation action_confirm", ok,
               f"state={data[0]['state']}" if data else "")
    else:
        record("P1", "Reservation action_confirm", False, "skipped")
except Exception as e:
    record("P1", "Reservation action_confirm", False, str(e))

# DELETE
try:
    if rv_id:
        mgr.unlink('booking.reservation', [rv_id])
        remaining = mgr.search('booking.reservation', [('id', '=', rv_id)])
        ok = len(remaining) == 0
        record("P1", "Reservation DELETE", ok, "deleted" if ok else f"still found")
        if ok:
            cleanup_ids['booking.reservation'].remove(rv_id)
    else:
        record("P1", "Reservation DELETE", False, "skipped")
except Exception as e:
    record("P1", "Reservation DELETE", False, str(e))

# ------------------------------------------------------------------
# 1.4  Search & Filter
# ------------------------------------------------------------------
print("\n--- 1.4 Search & Filter ---")

# Search by resource name
try:
    found = mgr.search_read('booking.resource.type',
                             [('name', 'ilike', 'Conference')],
                             fields=['name'])
    ok = any('Conference' in r['name'] for r in found)
    record("P1", "Search resource by name (ilike 'Conference')", ok,
           f"found {len(found)} record(s)")
except Exception as e:
    record("P1", "Search resource by name", False, str(e))

# For state/partner searches, create a temporary reservation
tmp_rv_id = None
try:
    tmp_rv_id = mgr.create('booking.reservation', {
        'resource_type_id': res_type_id,
        'start_datetime': '2026-03-26 09:00:00',
        'end_datetime': '2026-03-26 10:00:00',
        'partner_id': mgr_partner,
        'note': 'temp for search tests',
    })
    cleanup_ids['booking.reservation'].append(tmp_rv_id)
except Exception as e:
    record("P1", "Search setup (create temp reservation)", False, str(e))

# Search by state
try:
    found = mgr.search_read('booking.reservation',
                             [('state', '=', 'confirmed')],
                             fields=['name', 'state'])
    ok = len(found) > 0 and all(r['state'] == 'confirmed' for r in found)
    record("P1", "Search reservations by state='confirmed'", ok,
           f"found {len(found)} record(s)")
except Exception as e:
    record("P1", "Search reservations by state", False, str(e))

# Search by partner
try:
    found = mgr.search_read('booking.reservation',
                             [('partner_id', '=', mgr_partner)],
                             fields=['name', 'partner_id'])
    ok = len(found) > 0
    record("P1", "Search reservations by partner_id", ok,
           f"found {len(found)} for partner_id={mgr_partner}")
except Exception as e:
    record("P1", "Search reservations by partner_id", False, str(e))

# Cleanup temp reservation
if tmp_rv_id:
    try:
        mgr.unlink('booking.reservation', [tmp_rv_id])
        cleanup_ids['booking.reservation'].remove(tmp_rv_id)
    except Exception:
        pass

# ------------------------------------------------------------------
# 1.5  Availability CRUD
# ------------------------------------------------------------------
print("\n--- 1.5 Availability CRUD ---")

# CREATE
avail_id = None
try:
    avail_id = mgr.create('booking.resource.availability', {
        'resource_type_id': res_type_id,
        'dayofweek': '6',      # Sunday
        'hour_from': 10.0,
        'hour_to': 14.0,
    })
    cleanup_ids['booking.resource.availability'].append(avail_id)
    record("P1", "Availability CREATE", bool(avail_id), f"id={avail_id}")
except Exception as e:
    record("P1", "Availability CREATE", False, str(e))

# READ
try:
    if avail_id:
        data = mgr.read('booking.resource.availability', [avail_id],
                         fields=['resource_type_id', 'dayofweek', 'hour_from', 'hour_to'])
        d = data[0] if data else {}
        ok = d.get('dayofweek') == '6' and d.get('hour_from') == 10.0
        record("P1", "Availability READ", ok,
               f"day={d.get('dayofweek')}, from={d.get('hour_from')}, to={d.get('hour_to')}")
    else:
        record("P1", "Availability READ", False, "skipped")
except Exception as e:
    record("P1", "Availability READ", False, str(e))

# UPDATE hours
try:
    if avail_id:
        mgr.write('booking.resource.availability', [avail_id], {
            'hour_from': 8.0,
            'hour_to': 16.0,
        })
        data = mgr.read('booking.resource.availability', [avail_id],
                         fields=['hour_from', 'hour_to'])
        d = data[0] if data else {}
        ok = d.get('hour_from') == 8.0 and d.get('hour_to') == 16.0
        record("P1", "Availability UPDATE hours", ok,
               f"from={d.get('hour_from')}, to={d.get('hour_to')}")
    else:
        record("P1", "Availability UPDATE hours", False, "skipped")
except Exception as e:
    record("P1", "Availability UPDATE hours", False, str(e))

# DELETE
try:
    if avail_id:
        mgr.unlink('booking.resource.availability', [avail_id])
        remaining = mgr.search('booking.resource.availability', [('id', '=', avail_id)])
        ok = len(remaining) == 0
        record("P1", "Availability DELETE", ok, "deleted" if ok else "still found")
        if ok:
            cleanup_ids['booking.resource.availability'].remove(avail_id)
    else:
        record("P1", "Availability DELETE", False, "skipped")
except Exception as e:
    record("P1", "Availability DELETE", False, str(e))


# ===================================================================
# PHASE 2: User Permission Tests
# ===================================================================
section("PHASE 2: User Permission Tests (test_user)")

usr = OdooRPC("test_user", "test_user")
print(f"  Authenticated as test_user (uid={usr.uid})")
usr_partner = usr.read('res.users', [usr.uid], fields=['partner_id'])[0]['partner_id'][0]

# ------------------------------------------------------------------
# 2.1  CAN read resources
# ------------------------------------------------------------------
print("\n--- 2.1 Allowed operations ---")

try:
    resources = usr.search_read('booking.resource.type', [], fields=['name'])
    ok = len(resources) > 0
    record("P2", "CAN read resource types", ok, f"found {len(resources)} resource(s)")
except Exception as e:
    record("P2", "CAN read resource types", False, str(e))

# ------------------------------------------------------------------
# 2.2  CAN create own reservations
# ------------------------------------------------------------------
user_rv_id = None
try:
    user_rv_id = usr.create('booking.reservation', {
        'resource_type_id': res_type_id,
        'start_datetime': '2026-03-27 10:00:00',
        'end_datetime': '2026-03-27 11:00:00',
        'partner_id': usr_partner,
        'note': 'Phase 2 user reservation',
    })
    record("P2", "CAN create own reservation", bool(user_rv_id), f"id={user_rv_id}")
except Exception as e:
    record("P2", "CAN create own reservation", False, str(e))

# ------------------------------------------------------------------
# 2.3  CAN read own reservations
# ------------------------------------------------------------------
try:
    if user_rv_id:
        data = usr.read('booking.reservation', [user_rv_id],
                         fields=['name', 'state', 'partner_id'])
        ok = bool(data) and data[0]['partner_id'][0] == usr_partner
        record("P2", "CAN read own reservation", ok,
               f"state={data[0]['state']}" if data else "")
    else:
        record("P2", "CAN read own reservation", False, "no reservation created")
except Exception as e:
    record("P2", "CAN read own reservation", False, str(e))

# ------------------------------------------------------------------
# 2.4  CANNOT create/edit/delete categories
# ------------------------------------------------------------------
print("\n--- 2.2 Denied operations ---")

# CANNOT create category
try:
    usr.create('booking.resource.category', {'name': 'Should Fail'})
    record("P2", "CANNOT create category", False, "no error raised -- expected AccessError")
except Exception as e:
    record("P2", "CANNOT create category", is_access_error(e),
           f"correctly denied (fault={getattr(e, 'faultCode', '?')})")

# CANNOT edit category
try:
    usr.write('booking.resource.category', [CATEGORY_MEETING], {'name': 'Hacked'})
    record("P2", "CANNOT edit category", False, "no error raised -- expected AccessError")
except Exception as e:
    record("P2", "CANNOT edit category", is_access_error(e),
           f"correctly denied (fault={getattr(e, 'faultCode', '?')})")

# CANNOT delete category
try:
    usr.unlink('booking.resource.category', [CATEGORY_MEETING])
    record("P2", "CANNOT delete category", False, "no error raised -- expected AccessError")
except Exception as e:
    record("P2", "CANNOT delete category", is_access_error(e),
           f"correctly denied (fault={getattr(e, 'faultCode', '?')})")

# ------------------------------------------------------------------
# 2.5  CANNOT create/edit/delete resource types
# ------------------------------------------------------------------
# CANNOT create resource type
try:
    usr.create('booking.resource.type', {
        'name': 'Should Fail Room',
        'category_id': CATEGORY_MEETING,
        'slot_duration': 1.0,
        'slot_interval': 1.0,
        'advance_days': 7,
    })
    record("P2", "CANNOT create resource type", False, "no error raised -- expected AccessError")
except Exception as e:
    record("P2", "CANNOT create resource type", is_access_error(e),
           f"correctly denied (fault={getattr(e, 'faultCode', '?')})")

# CANNOT edit resource type
try:
    usr.write('booking.resource.type', [res_type_id], {'name': 'Hacked Room'})
    record("P2", "CANNOT edit resource type", False, "no error raised -- expected AccessError")
except Exception as e:
    record("P2", "CANNOT edit resource type", is_access_error(e),
           f"correctly denied (fault={getattr(e, 'faultCode', '?')})")

# CANNOT delete resource type
try:
    usr.unlink('booking.resource.type', [res_type_id])
    record("P2", "CANNOT delete resource type", False, "no error raised -- expected AccessError")
except Exception as e:
    record("P2", "CANNOT delete resource type", is_access_error(e),
           f"correctly denied (fault={getattr(e, 'faultCode', '?')})")

# ------------------------------------------------------------------
# 2.6  CANNOT delete reservations
# ------------------------------------------------------------------
try:
    if user_rv_id:
        usr.unlink('booking.reservation', [user_rv_id])
        record("P2", "CANNOT delete reservation", False, "no error raised -- expected AccessError")
    else:
        record("P2", "CANNOT delete reservation", False, "no reservation to test with")
except Exception as e:
    record("P2", "CANNOT delete reservation", is_access_error(e),
           f"correctly denied (fault={getattr(e, 'faultCode', '?')})")

# ------------------------------------------------------------------
# 2.7  CAN cancel own reservation via action_cancel
# ------------------------------------------------------------------
try:
    if user_rv_id:
        call_action(usr, 'booking.reservation', 'action_cancel', [user_rv_id])
        data = usr.read('booking.reservation', [user_rv_id], fields=['state'])
        ok = data and data[0]['state'] == 'cancelled'
        record("P2", "CAN cancel own reservation via action_cancel", ok,
               f"state={data[0]['state']}" if data else "")
    else:
        record("P2", "CAN cancel own reservation via action_cancel", False, "no reservation")
except Exception as e:
    record("P2", "CAN cancel own reservation via action_cancel", False, str(e))


# ===================================================================
# CLEANUP
# ===================================================================
section("CLEANUP")

# Use manager to clean up any leftover test records
for model, ids in cleanup_ids.items():
    for rec_id in ids:
        try:
            mgr.unlink(model, [rec_id])
            print(f"  Cleaned up {model} id={rec_id}")
        except Exception:
            pass

# Also clean up the user's reservation if it still exists
if user_rv_id:
    try:
        mgr.unlink('booking.reservation', [user_rv_id])
        print(f"  Cleaned up booking.reservation id={user_rv_id}")
    except Exception:
        pass


# ===================================================================
# SUMMARY
# ===================================================================
section("TEST SUMMARY")

p1_results = [(n, p, d) for (ph, n, p, d) in results if ph == "P1"]
p2_results = [(n, p, d) for (ph, n, p, d) in results if ph == "P2"]

p1_pass = sum(1 for _, p, _ in p1_results if p)
p1_fail = sum(1 for _, p, _ in p1_results if not p)
p2_pass = sum(1 for _, p, _ in p2_results if p)
p2_fail = sum(1 for _, p, _ in p2_results if not p)

total_pass = p1_pass + p2_pass
total_fail = p1_fail + p2_fail
total = total_pass + total_fail

print(f"\n  Phase 1 (Manager CRUD):       {p1_pass}/{len(p1_results)} passed")
print(f"  Phase 2 (User Permissions):   {p2_pass}/{len(p2_results)} passed")
print(f"  {'=' * 40}")
print(f"  TOTAL:                        {total_pass}/{total} passed, {total_fail} failed")

if total_fail > 0:
    print(f"\n  FAILED tests:")
    for phase, name, passed, detail in results:
        if not passed:
            print(f"    [{phase}] {name}: {detail}")

print()
sys.exit(0 if total_fail == 0 else 1)
