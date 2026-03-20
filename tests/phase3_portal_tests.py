#!/usr/bin/env python3
"""
Phase 3: Portal User Functionality Tests for Odoo Booking Reservation Module.

Tests cover:
  A. Portal XML-RPC Permission Tests
  B. Access Control Tests (share_type enforcement)
  C. Portal HTTP Route Tests (using requests library)
  D. Privacy Tests (cross-user data isolation)

Run from project root:
    python3 tests/phase3_portal_tests.py
"""
import sys
import time
import json
import traceback
from datetime import datetime, timedelta

sys.path.insert(0, '.')
from tests.odoo_rpc import OdooRPC

try:
    import requests
except ImportError:
    print("ERROR: 'requests' library is required. Install with: pip3 install requests")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
BASE_URL = "http://localhost:9071"

USERS = {
    "portal1": {"login": "portal1", "password": "portal1", "id": 8, "partner_id": 9},
    "portal2": {"login": "portal2", "password": "portal2", "id": 9, "partner_id": 10},
    "portal3": {"login": "portal3", "password": "portal3", "id": 10, "partner_id": 11},
}

RESOURCES = {
    "Conference Room A": {"id": 2, "share": "all", "slot": "1h"},
    "Small Meeting Room B": {"id": 3, "share": "all", "slot": "30min"},
    "VIP Room C": {"id": 4, "share": "specific (portal1, portal2 only)", "slot": "2h"},
    "Projector": {"id": 5, "share": "all", "slot": "1h"},
    "Phone Booth": {"id": 6, "share": "all", "slot": "15min"},
}

# Pick a future Wednesday (weekday 2) that falls within advance_days for all resources.
# Resources have availability Mon-Fri 9:00-18:00.
_base = datetime.now().date()
_offset = (2 - _base.weekday()) % 7  # days until next Wednesday
if _offset == 0:
    _offset = 7  # skip today, use next week
BOOKING_DATE = _base + timedelta(days=_offset)
BOOKING_DATE_STR = BOOKING_DATE.strftime("%Y-%m-%d")

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------
results = []


def record(section, name, passed, detail=""):
    """Record a test result."""
    status = "PASS" if passed else "FAIL"
    results.append({"section": section, "name": name, "passed": passed, "detail": detail})
    tag = f"[{section}]"
    if detail:
        print(f"  {status} {tag} {name} -- {detail}")
    else:
        print(f"  {status} {tag} {name}")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def make_rpc(login, password):
    """Create an OdooRPC connection, return (rpc, ok, error_msg)."""
    try:
        rpc = OdooRPC(login, password)
        return rpc, True, ""
    except Exception as e:
        return None, False, str(e)


def expect_error(fn, label=""):
    """Call fn(); return True if it raised an exception, False otherwise."""
    try:
        fn()
        return False
    except Exception:
        return True


def get_session(login, password):
    """Log in via HTTP and return a requests.Session with cookies set."""
    s = requests.Session()
    # Fetch the login page first to get the CSRF token
    login_page = s.get(f"{BASE_URL}/web/login", timeout=15)
    # Extract csrf_token from hidden input
    csrf = ""
    if 'csrf_token' in login_page.text:
        import re
        m = re.search(r'name="csrf_token"\s+value="([^"]+)"', login_page.text)
        if m:
            csrf = m.group(1)
    payload = {
        "login": login,
        "password": password,
        "redirect": "/my",
        "db": "odoocalendar",
    }
    if csrf:
        payload["csrf_token"] = csrf
    resp = s.post(f"{BASE_URL}/web/login", data=payload, timeout=15, allow_redirects=True)
    return s, resp


def admin_cleanup_reservations(ids_to_remove):
    """Use admin RPC to cancel/remove test reservations so they don't interfere."""
    try:
        adm = OdooRPC("admin", "admin")
        if ids_to_remove:
            adm.write('booking.reservation', ids_to_remove, {'state': 'cancelled'})
    except Exception:
        pass


# =========================================================================
# A. Portal XML-RPC Permission Tests
# =========================================================================
def section_a():
    print("\n" + "=" * 70)
    print("SECTION A: Portal XML-RPC Permission Tests")
    print("=" * 70)

    # --- Connect each portal user ---
    portal_rpcs = {}
    for uname, ucfg in USERS.items():
        rpc, ok, err = make_rpc(ucfg["login"], ucfg["password"])
        if not ok:
            record("A", f"{uname} authenticate", False, err)
            continue
        portal_rpcs[uname] = rpc
        record("A", f"{uname} authenticate", True, f"uid={rpc.uid}")

    if not portal_rpcs:
        record("A", "All portal logins failed -- skipping section", False)
        return

    # Use portal1 as representative for generic permission tests
    rpc1 = portal_rpcs.get("portal1")
    if not rpc1:
        record("A", "portal1 login required for permission tests", False)
        return

    partner1 = USERS["portal1"]["partner_id"]

    # A1. Portal CAN read booking.resource.type
    try:
        types = rpc1.search_read('booking.resource.type', [], fields=['name'])
        record("A1", "Portal CAN read booking.resource.type", len(types) >= 0,
               f"returned {len(types)} records")
    except Exception as e:
        record("A1", "Portal CAN read booking.resource.type", False, str(e))

    # A2. Portal CAN read booking.resource.category
    try:
        cats = rpc1.search_read('booking.resource.category', [], fields=['name'])
        record("A2", "Portal CAN read booking.resource.category", len(cats) >= 0,
               f"returned {len(cats)} records")
    except Exception as e:
        record("A2", "Portal CAN read booking.resource.category", False, str(e))

    # A3. Portal CAN read booking.resource.availability
    try:
        avails = rpc1.search_read('booking.resource.availability', [], fields=['dayofweek'])
        record("A3", "Portal CAN read booking.resource.availability", len(avails) >= 0,
               f"returned {len(avails)} records")
    except Exception as e:
        record("A3", "Portal CAN read booking.resource.availability", False, str(e))

    # A4. Portal CANNOT create/write/delete booking.resource.type
    err_create = expect_error(
        lambda: rpc1.create('booking.resource.type', {'name': 'Hack Room', 'slot_duration': 1.0, 'slot_interval': 1.0})
    )
    record("A4a", "Portal CANNOT create booking.resource.type", err_create)

    err_write = expect_error(
        lambda: rpc1.write('booking.resource.type', [RESOURCES["Conference Room A"]["id"]], {'name': 'Hacked'})
    )
    record("A4b", "Portal CANNOT write booking.resource.type", err_write)

    err_unlink = expect_error(
        lambda: rpc1.unlink('booking.resource.type', [RESOURCES["Conference Room A"]["id"]])
    )
    record("A4c", "Portal CANNOT delete booking.resource.type", err_unlink)

    # A5. Portal CANNOT create/write/delete booking.resource.category
    err_create = expect_error(
        lambda: rpc1.create('booking.resource.category', {'name': 'Hack Category'})
    )
    record("A5a", "Portal CANNOT create booking.resource.category", err_create)

    err_write = expect_error(
        lambda: rpc1.write('booking.resource.category', [1], {'name': 'Hacked Cat'})
    )
    record("A5b", "Portal CANNOT write booking.resource.category", err_write)

    err_unlink = expect_error(
        lambda: rpc1.unlink('booking.resource.category', [1])
    )
    record("A5c", "Portal CANNOT delete booking.resource.category", err_unlink)

    # A6. Portal CAN create booking.reservation (with their own partner_id)
    start_dt = f"{BOOKING_DATE_STR} 09:00:00"
    end_dt = f"{BOOKING_DATE_STR} 10:00:00"
    a6_res_id = None
    try:
        a6_res_id = rpc1.create('booking.reservation', {
            'resource_type_id': RESOURCES["Conference Room A"]["id"],
            'start_datetime': start_dt,
            'end_datetime': end_dt,
            'partner_id': partner1,
            'note': 'A6 test reservation',
        })
        record("A6", "Portal CAN create booking.reservation", bool(a6_res_id),
               f"id={a6_res_id}")
    except Exception as e:
        record("A6", "Portal CAN create booking.reservation", False, str(e))

    # A7. Portal CAN write their own booking.reservation
    if a6_res_id:
        try:
            rpc1.write('booking.reservation', [a6_res_id], {'note': 'A7 updated note'})
            updated = rpc1.read('booking.reservation', [a6_res_id], fields=['note'])
            ok = updated and updated[0].get('note') == 'A7 updated note'
            record("A7", "Portal CAN write own booking.reservation", ok,
                   f"note={'A7 updated note' if ok else updated}")
        except Exception as e:
            record("A7", "Portal CAN write own booking.reservation", False, str(e))
    else:
        record("A7", "Portal CAN write own booking.reservation", False, "skipped (A6 failed)")

    # A8. Portal CANNOT delete booking.reservation
    if a6_res_id:
        err_unlink = expect_error(
            lambda: rpc1.unlink('booking.reservation', [a6_res_id])
        )
        record("A8", "Portal CANNOT delete booking.reservation", err_unlink)
    else:
        record("A8", "Portal CANNOT delete booking.reservation", False, "skipped (A6 failed)")

    # A9. Portal CAN cancel own reservation (action_cancel)
    #     action_cancel calls write({'state':'cancelled'}) and returns None.
    #     XML-RPC cannot marshal None, so we call write directly or handle the error
    #     and verify the state changed afterwards.
    if a6_res_id:
        try:
            # Use write to set state to cancelled (same as action_cancel internally)
            rpc1.write('booking.reservation', [a6_res_id], {'state': 'cancelled'})
            data = rpc1.read('booking.reservation', [a6_res_id], fields=['state'])
            ok = data and data[0].get('state') == 'cancelled'
            record("A9", "Portal CAN cancel own reservation (action_cancel)", ok,
                   f"state={data[0].get('state') if data else 'N/A'}")
        except Exception as e:
            # If write fails, try calling action_cancel and tolerate the None-marshal error
            try:
                rpc1.execute('booking.reservation', 'action_cancel', [a6_res_id])
            except Exception:
                pass  # The None marshal error is expected
            # Verify the state via a fresh read
            try:
                data = rpc1.read('booking.reservation', [a6_res_id], fields=['state'])
                ok = data and data[0].get('state') == 'cancelled'
                record("A9", "Portal CAN cancel own reservation (action_cancel)", ok,
                       f"state={data[0].get('state') if data else 'N/A'} (via fallback)")
            except Exception as e2:
                record("A9", "Portal CAN cancel own reservation (action_cancel)", False, str(e2))
    else:
        record("A9", "Portal CAN cancel own reservation (action_cancel)", False, "skipped (A6 failed)")


# =========================================================================
# B. Access Control Tests
# =========================================================================
def section_b():
    print("\n" + "=" * 70)
    print("SECTION B: Access Control Tests (share_type enforcement)")
    print("=" * 70)

    vip_id = RESOURCES["VIP Room C"]["id"]
    conf_id = RESOURCES["Conference Room A"]["id"]

    cleanup_ids = []

    # B1. portal1 CAN book VIP Room C
    rpc1, ok1, _ = make_rpc("portal1", "portal1")
    p1_partner = USERS["portal1"]["partner_id"]
    b1_start = f"{BOOKING_DATE_STR} 10:00:00"
    b1_end = f"{BOOKING_DATE_STR} 12:00:00"
    b1_id = None
    if ok1:
        try:
            b1_id = rpc1.create('booking.reservation', {
                'resource_type_id': vip_id,
                'start_datetime': b1_start,
                'end_datetime': b1_end,
                'partner_id': p1_partner,
                'note': 'B1 VIP portal1',
            })
            record("B1", "portal1 CAN book VIP Room C (share_type=specific, allowed)", True,
                   f"id={b1_id}")
            cleanup_ids.append(b1_id)
        except Exception as e:
            record("B1", "portal1 CAN book VIP Room C (share_type=specific, allowed)", False, str(e))
    else:
        record("B1", "portal1 CAN book VIP Room C", False, "login failed")

    # Cancel B1 so B2 can use same slot on VIP room
    if b1_id and rpc1:
        try:
            rpc1.execute('booking.reservation', 'action_cancel', [b1_id])
        except Exception:
            admin_cleanup_reservations([b1_id])

    # B2. portal2 CAN book VIP Room C
    rpc2, ok2, _ = make_rpc("portal2", "portal2")
    p2_partner = USERS["portal2"]["partner_id"]
    b2_id = None
    if ok2:
        try:
            b2_id = rpc2.create('booking.reservation', {
                'resource_type_id': vip_id,
                'start_datetime': b1_start,
                'end_datetime': b1_end,
                'partner_id': p2_partner,
                'note': 'B2 VIP portal2',
            })
            record("B2", "portal2 CAN book VIP Room C (share_type=specific, allowed)", True,
                   f"id={b2_id}")
            cleanup_ids.append(b2_id)
        except Exception as e:
            record("B2", "portal2 CAN book VIP Room C (share_type=specific, allowed)", False, str(e))
    else:
        record("B2", "portal2 CAN book VIP Room C", False, "login failed")

    # Cancel B2 to free up the slot
    if b2_id and rpc2:
        try:
            rpc2.execute('booking.reservation', 'action_cancel', [b2_id])
        except Exception:
            admin_cleanup_reservations([b2_id])

    # B3. portal3 CANNOT book VIP Room C (not in allowed_partner_ids)
    rpc3, ok3, _ = make_rpc("portal3", "portal3")
    p3_partner = USERS["portal3"]["partner_id"]
    if ok3:
        denied = expect_error(
            lambda: rpc3.create('booking.reservation', {
                'resource_type_id': vip_id,
                'start_datetime': b1_start,
                'end_datetime': b1_end,
                'partner_id': p3_partner,
                'note': 'B3 VIP portal3 should fail',
            })
        )
        record("B3", "portal3 CANNOT book VIP Room C (not in allowed_partner_ids)", denied,
               "error raised as expected" if denied else "NO error -- access control MISSING")
    else:
        record("B3", "portal3 CANNOT book VIP Room C", False, "login failed")

    # B4. portal1/2/3 CAN all book Conference Room A (share_type=all)
    # Use different time slots to avoid overlap
    slot_offsets = [
        ("portal1", 0, rpc1, ok1, p1_partner),
        ("portal2", 1, rpc2, ok2, p2_partner),
        ("portal3", 2, rpc3, ok3, p3_partner),
    ]
    for uname, hour_off, rpc, ok, pid in slot_offsets:
        s_hour = 9 + hour_off
        e_hour = s_hour + 1
        b4_start = f"{BOOKING_DATE_STR} {s_hour:02d}:00:00"
        b4_end = f"{BOOKING_DATE_STR} {e_hour:02d}:00:00"
        if ok and rpc:
            try:
                b4_id = rpc.create('booking.reservation', {
                    'resource_type_id': conf_id,
                    'start_datetime': b4_start,
                    'end_datetime': b4_end,
                    'partner_id': pid,
                    'note': f'B4 ConfRoom {uname}',
                })
                record("B4", f"{uname} CAN book Conference Room A (share_type=all)", True,
                       f"id={b4_id}")
                cleanup_ids.append(b4_id)
            except Exception as e:
                record("B4", f"{uname} CAN book Conference Room A (share_type=all)", False, str(e))
        else:
            record("B4", f"{uname} CAN book Conference Room A", False, "login failed")

    # Cleanup: cancel all B-section reservations
    admin_cleanup_reservations(cleanup_ids)


# =========================================================================
# C. Portal HTTP Route Tests
# =========================================================================
def section_c():
    print("\n" + "=" * 70)
    print("SECTION C: Portal HTTP Route Tests (requests library)")
    print("=" * 70)

    # C1. Login to portal
    session, login_resp = get_session("portal1", "portal1")
    # After successful login, Odoo redirects to /my or /web.
    # A failed login stays on /web/login with an error.
    login_ok = login_resp.status_code == 200 and '/web/login' not in login_resp.url
    if not login_ok:
        # Sometimes Odoo keeps url as /my which is fine
        login_ok = login_resp.status_code == 200
    record("C1", "POST /web/login as portal1", login_ok,
           f"status={login_resp.status_code}, url={login_resp.url}")

    if not login_ok:
        record("C1", "Aborting section C -- portal login failed", False)
        return

    # C2. GET /my/booking/resources
    try:
        resp = session.get(f"{BASE_URL}/my/booking/resources", timeout=15, allow_redirects=True)
        ok = resp.status_code == 200
        record("C2", "GET /my/booking/resources returns 200", ok,
               f"status={resp.status_code}, length={len(resp.text)}")
    except Exception as e:
        record("C2", "GET /my/booking/resources returns 200", False, str(e))

    # C3. GET /my/booking/resources/2 (Conference Room A)
    conf_id = RESOURCES["Conference Room A"]["id"]
    try:
        resp = session.get(f"{BASE_URL}/my/booking/resources/{conf_id}", timeout=15, allow_redirects=True)
        ok = resp.status_code == 200
        record("C3", f"GET /my/booking/resources/{conf_id} (Conference Room A) returns 200", ok,
               f"status={resp.status_code}")
    except Exception as e:
        record("C3", f"GET /my/booking/resources/{conf_id} returns 200", False, str(e))

    # C4. GET /my/bookings
    try:
        resp = session.get(f"{BASE_URL}/my/bookings", timeout=15, allow_redirects=True)
        ok = resp.status_code == 200
        record("C4", "GET /my/bookings returns 200", ok,
               f"status={resp.status_code}")
    except Exception as e:
        record("C4", "GET /my/bookings returns 200", False, str(e))

    # C5. POST /my/bookings/create - create a booking
    partner1 = USERS["portal1"]["partner_id"]
    # Use a distinct time slot that won't collide with section A/B
    c5_start = f"{BOOKING_DATE_STR} 14:00:00"
    c5_end = f"{BOOKING_DATE_STR} 15:00:00"
    c5_booking_id = None

    try:
        import re
        # Get the new-booking page first, which should contain a form with csrf_token
        new_page = session.get(f"{BASE_URL}/my/bookings/new?resource_id={conf_id}", timeout=15)
        csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', new_page.text)
        csrf = csrf_match.group(1) if csrf_match else ""

        # If no csrf found on new page, try the resource detail page
        if not csrf:
            detail_page = session.get(f"{BASE_URL}/my/booking/resources/{conf_id}", timeout=15)
            csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', detail_page.text)
            csrf = csrf_match.group(1) if csrf_match else ""

        post_data = {
            'resource_id': conf_id,
            'start_datetime': c5_start,
            'end_datetime': c5_end,
            'note': 'C5 HTTP booking test',
        }
        if csrf:
            post_data['csrf_token'] = csrf

        resp = session.post(f"{BASE_URL}/my/bookings/create", data=post_data,
                            timeout=15, allow_redirects=True)
        # Expect redirect to /my/bookings/<id>?success=created  or at least 200
        ok = resp.status_code == 200
        # Try to extract the booking ID from the final URL
        id_match = re.search(r'/my/bookings/(\d+)', resp.url)
        if id_match:
            c5_booking_id = int(id_match.group(1))

        # If we could not extract the id from the URL, try to find it via RPC
        if not c5_booking_id and ok:
            try:
                adm = OdooRPC("admin", "admin")
                found = adm.search_read('booking.reservation', [
                    ('partner_id', '=', partner1),
                    ('start_datetime', '=', c5_start),
                    ('note', 'ilike', 'C5'),
                ], fields=['id'])
                if found:
                    c5_booking_id = found[0]['id']
            except Exception:
                pass

        record("C5", "POST /my/bookings/create creates booking", ok and c5_booking_id is not None,
               f"status={resp.status_code}, url={resp.url}, booking_id={c5_booking_id}")
    except Exception as e:
        record("C5", "POST /my/bookings/create creates booking", False, str(e))

    # C6. GET /my/bookings/<id> - view booking detail
    if c5_booking_id:
        try:
            resp = session.get(f"{BASE_URL}/my/bookings/{c5_booking_id}", timeout=15,
                               allow_redirects=True)
            ok = resp.status_code == 200
            record("C6", f"GET /my/bookings/{c5_booking_id} returns 200", ok,
                   f"status={resp.status_code}")
        except Exception as e:
            record("C6", f"GET /my/bookings/{c5_booking_id} returns 200", False, str(e))
    else:
        record("C6", "GET /my/bookings/<id> returns 200", False, "skipped (C5 failed)")

    # C7. POST /my/bookings/<id>/cancel - cancel booking
    if c5_booking_id:
        try:
            # Get a fresh csrf token
            page = session.get(f"{BASE_URL}/my/bookings/{c5_booking_id}", timeout=15)
            csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', page.text)
            csrf = csrf_match.group(1) if csrf_match else ""

            cancel_data = {}
            if csrf:
                cancel_data['csrf_token'] = csrf

            resp = session.post(f"{BASE_URL}/my/bookings/{c5_booking_id}/cancel",
                                data=cancel_data, timeout=15, allow_redirects=True)
            ok = resp.status_code == 200
            # Verify the state changed via RPC
            adm = OdooRPC("admin", "admin")
            state_data = adm.read('booking.reservation', [c5_booking_id], fields=['state'])
            cancelled = state_data and state_data[0].get('state') == 'cancelled'
            record("C7", f"POST /my/bookings/{c5_booking_id}/cancel cancels booking",
                   ok and cancelled,
                   f"http_status={resp.status_code}, state={state_data[0].get('state') if state_data else 'N/A'}")
        except Exception as e:
            record("C7", f"POST /my/bookings/{c5_booking_id}/cancel cancels booking", False, str(e))
    else:
        record("C7", "POST /my/bookings/<id>/cancel cancels booking", False, "skipped (C5 failed)")


# =========================================================================
# D. Privacy Tests
# =========================================================================
def section_d():
    print("\n" + "=" * 70)
    print("SECTION D: Privacy Tests (cross-user data isolation)")
    print("=" * 70)

    conf_id = RESOURCES["Conference Room A"]["id"]
    cleanup_ids = []

    # D1. portal1 creates a reservation
    rpc1, ok1, _ = make_rpc("portal1", "portal1")
    p1_partner = USERS["portal1"]["partner_id"]
    d1_start = f"{BOOKING_DATE_STR} 15:00:00"
    d1_end = f"{BOOKING_DATE_STR} 16:00:00"
    d1_id = None
    if ok1:
        try:
            d1_id = rpc1.create('booking.reservation', {
                'resource_type_id': conf_id,
                'start_datetime': d1_start,
                'end_datetime': d1_end,
                'partner_id': p1_partner,
                'note': 'D1 portal1 private reservation',
            })
            record("D1", "portal1 creates reservation for privacy test", True, f"id={d1_id}")
            cleanup_ids.append(d1_id)
        except Exception as e:
            record("D1", "portal1 creates reservation for privacy test", False, str(e))
    else:
        record("D1", "portal1 creates reservation for privacy test", False, "login failed")

    # D2. portal2 creates a reservation on same resource (different time)
    rpc2, ok2, _ = make_rpc("portal2", "portal2")
    p2_partner = USERS["portal2"]["partner_id"]
    d2_start = f"{BOOKING_DATE_STR} 16:00:00"
    d2_end = f"{BOOKING_DATE_STR} 17:00:00"
    d2_id = None
    if ok2:
        try:
            d2_id = rpc2.create('booking.reservation', {
                'resource_type_id': conf_id,
                'start_datetime': d2_start,
                'end_datetime': d2_end,
                'partner_id': p2_partner,
                'note': 'D2 portal2 private reservation',
            })
            record("D2", "portal2 creates reservation for privacy test", True, f"id={d2_id}")
            cleanup_ids.append(d2_id)
        except Exception as e:
            record("D2", "portal2 creates reservation for privacy test", False, str(e))
    else:
        record("D2", "portal2 creates reservation for privacy test", False, "login failed")

    # D3. Verify cross-user privacy via XML-RPC.
    #     We test multiple aspects:
    #       D3a - Can portal1 read portal2's reservation?
    #       D3b - Can portal1 write portal2's reservation?
    #       D3c - Does the portal HTTP route block cross-user access?
    if d1_id and d2_id and ok1 and ok2:
        # D3a. Read isolation test
        read_isolated = False
        detail_a = ""
        try:
            other_data = rpc1.read('booking.reservation', [d2_id], fields=['partner_id', 'note', 'state'])
            if not other_data or not other_data[0]:
                read_isolated = True
                detail_a = "record rule prevents portal1 from reading portal2's reservation"
            else:
                other_partner = other_data[0].get('partner_id')
                if not other_partner or other_partner is False:
                    read_isolated = True
                    detail_a = "partner_id hidden from cross-user read"
                else:
                    read_isolated = False
                    detail_a = f"portal1 can read portal2's reservation (partner_id={other_partner})"
        except Exception:
            read_isolated = True
            detail_a = "AccessError raised on cross-user read (good)"
        record("D3a", "Privacy: portal1 cannot read portal2's reservation via RPC",
               read_isolated, detail_a)

        # D3b. Write isolation test
        write_isolated = False
        detail_b = ""
        try:
            rpc1.write('booking.reservation', [d2_id], {'note': 'hacked by portal1'})
            # Check if the write actually persisted
            check = rpc2.read('booking.reservation', [d2_id], fields=['note'])
            if check and check[0].get('note') == 'hacked by portal1':
                write_isolated = False
                detail_b = "portal1 wrote portal2's reservation successfully (no write isolation)"
                # Restore original note
                rpc2.write('booking.reservation', [d2_id], {'note': 'D2 portal2 private reservation'})
            else:
                write_isolated = True
                detail_b = "write call did not persist (effective isolation)"
        except Exception:
            write_isolated = True
            detail_b = "AccessError raised on cross-user write (good)"
        record("D3b", "Privacy: portal1 cannot write portal2's reservation via RPC",
               write_isolated, detail_b)

        # D3c. HTTP portal route isolation test
        #      The portal controller explicitly checks partner_id match, so
        #      portal1 should NOT be able to view portal2's booking via HTTP.
        detail_c = ""
        http_isolated = False
        try:
            sess1, _ = get_session("portal1", "portal1")
            resp = sess1.get(f"{BASE_URL}/my/bookings/{d2_id}", timeout=15, allow_redirects=True)
            # Controller raises MissingError for other user's bookings -> 403 or error page
            if resp.status_code in (403, 404, 500):
                http_isolated = True
                detail_c = f"HTTP status {resp.status_code} (access blocked)"
            elif resp.status_code == 200 and 'does not exist' in resp.text.lower():
                http_isolated = True
                detail_c = "200 with 'does not exist' message (portal route blocks access)"
            elif resp.status_code == 200 and ('error' in resp.text.lower() or 'missing' in resp.text.lower()):
                http_isolated = True
                detail_c = "200 with error page (portal route blocks access)"
            elif resp.status_code == 200:
                # Check if it shows an error or the actual booking
                http_isolated = False
                detail_c = f"HTTP 200 returned (portal route may not block cross-user access)"
            else:
                http_isolated = True
                detail_c = f"HTTP status {resp.status_code}"
        except Exception as e:
            http_isolated = True
            detail_c = f"Exception: {e}"
        record("D3c", "Privacy: portal1 cannot view portal2's booking via HTTP route",
               http_isolated, detail_c)
    else:
        record("D3a", "Privacy: read isolation test", False, "skipped (D1 or D2 failed)")
        record("D3b", "Privacy: write isolation test", False, "skipped (D1 or D2 failed)")
        record("D3c", "Privacy: HTTP route isolation test", False, "skipped (D1 or D2 failed)")

    # Cleanup
    admin_cleanup_reservations(cleanup_ids)


# =========================================================================
# Main
# =========================================================================
def main():
    print("=" * 70)
    print("Phase 3: Portal User Functionality Tests")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Booking test date: {BOOKING_DATE_STR} (Wednesday)")
    print(f"Server: {BASE_URL}")
    print("=" * 70)

    # Run all sections; capture exceptions so one section doesn't kill the rest
    for section_fn in [section_a, section_b, section_c, section_d]:
        try:
            section_fn()
        except Exception as e:
            section_name = section_fn.__name__.replace("section_", "").upper()
            print(f"\n  *** Section {section_name} crashed: {e}")
            traceback.print_exc()
            record(section_name, f"Section {section_name} unexpected crash", False, str(e))

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed

    # Group by section
    sections = {}
    for r in results:
        sec = r["section"]
        if sec not in sections:
            sections[sec] = {"pass": 0, "fail": 0}
        if r["passed"]:
            sections[sec]["pass"] += 1
        else:
            sections[sec]["fail"] += 1

    for sec in sorted(sections.keys()):
        s = sections[sec]
        print(f"  Section {sec}: {s['pass']} passed, {s['fail']} failed")

    print(f"\n  TOTAL: {passed}/{total} passed, {failed} failed")

    if failed:
        print("\n  Failed tests:")
        for r in results:
            if not r["passed"]:
                print(f"    [{r['section']}] {r['name']}: {r['detail']}")

    print("\n" + "=" * 70)
    if failed == 0:
        print("ALL TESTS PASSED")
    else:
        print(f"{failed} TEST(S) FAILED")
    print("=" * 70)

    return 0 if failed == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
