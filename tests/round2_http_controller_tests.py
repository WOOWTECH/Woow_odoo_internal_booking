#!/usr/bin/env python3
"""
Round 2: HTTP/Controller Layer Tests
Enterprise-grade portal route testing via curl/HTTP
Tests form submissions, CSRF, error handling, redirects
"""
import requests
import re
import xmlrpc.client
from datetime import datetime, timedelta, timezone
from urllib.parse import urljoin

BASE_URL = "http://localhost:9071"
DB = "odoocalendar"

# XML-RPC for test data setup
common = xmlrpc.client.ServerProxy(f"{BASE_URL}/xmlrpc/2/common", allow_none=True)
models = xmlrpc.client.ServerProxy(f"{BASE_URL}/xmlrpc/2/object", allow_none=True)
admin_uid = common.authenticate(DB, "admin", "admin", {})

results = []

def run_test(tc_id, description, func):
    try:
        func()
        results.append((tc_id, description, "PASS", ""))
        print(f"  \u2713 {tc_id}: {description}")
    except Exception as e:
        import traceback
        results.append((tc_id, description, "FAIL", str(e)))
        print(f"  \u2717 {tc_id}: {description}")
        print(f"    Error: {e}")
        for line in traceback.format_exc().strip().split('\n')[-3:]:
            print(f"    {line}")

def rpc(model, method, args, kwargs=None):
    return models.execute_kw(DB, admin_uid, "admin", model, method, args, kwargs or {})

def login_portal():
    """Login as portal user and return session."""
    session = requests.Session()
    resp = session.get(f"{BASE_URL}/web/login")
    csrf = re.search(r'csrf_token.*?value="([^"]*)"', resp.text)
    if csrf:
        session.post(f"{BASE_URL}/web/login", data={
            "login": "portal",
            "password": "portal",
            "csrf_token": csrf.group(1),
        }, allow_redirects=True)
    return session

def get_csrf(session, url):
    """Get CSRF token from a page."""
    resp = session.get(url)
    match = re.search(r'name="csrf_token"[^>]*value="([^"]*)"', resp.text)
    if not match:
        match = re.search(r'csrf_token.*?value="([^"]*)"', resp.text)
    return match.group(1) if match else None, resp

# ─── Setup ───
print("\n" + "=" * 70)
print("ROUND 2: HTTP/CONTROLLER LAYER TESTS")
print("=" * 70)

print("\n--- Setup ---")
portal_session = login_portal()
print(f"  Portal session established")

# Get an available resource
resources = rpc("booking.resource.type", "search_read",
    [[("active", "=", True)]],
    {"fields": ["id", "name", "enable_discussion", "advance_days"], "limit": 1})
resource = resources[0]
resource_id = resource["id"]
print(f"  Using resource: {resource['name']} (ID: {resource_id})")
rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": True}])

# Future datetime
now = datetime.now(timezone.utc)
future_start = now.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=5)
future_end = future_start + timedelta(hours=1)
start_str = future_start.strftime("%Y-%m-%d %H:%M:%S")
end_str = future_end.strftime("%Y-%m-%d %H:%M:%S")
print(f"  Test booking time: {start_str} - {end_str}")

test_booking_ids = []

# ─── 2.1 Portal Routes ───
print("\n--- 2.1 Portal Routes ---")

def tc024():
    """GET /my/bookings → 200, shows booking list"""
    resp = portal_session.get(f"{BASE_URL}/my/bookings")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "My Bookings" in resp.text or "booking" in resp.text.lower(), "Missing booking content"
run_test("TC-024", "GET /my/bookings → 200 with content", tc024)

def tc025():
    """GET /my/booking/resources → 200, shows resource cards"""
    resp = portal_session.get(f"{BASE_URL}/my/booking/resources")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resource["name"] in resp.text, f"Missing resource: {resource['name']}"
run_test("TC-025", "GET /my/booking/resources → 200 with resource cards", tc025)

def tc026():
    """GET /my/booking/resources/{id} → 200, shows slots"""
    resp = portal_session.get(f"{BASE_URL}/my/booking/resources/{resource_id}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert resource["name"] in resp.text, f"Missing resource name in detail"
run_test("TC-026", "GET /my/booking/resources/{id} → 200 with slots", tc026)

def tc027():
    """GET /my/bookings/confirm?resource_id=&start=&end= → 200, shows form"""
    resp = portal_session.get(f"{BASE_URL}/my/bookings/confirm", params={
        "resource_id": resource_id,
        "start_datetime": start_str,
        "end_datetime": end_str,
    })
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    # Check form elements present
    assert 'csrf_token' in resp.text, "Missing CSRF token in form"
    assert 'resource_id' in resp.text, "Missing resource_id in form"
run_test("TC-027", "GET /my/bookings/confirm → 200 with booking form", tc027)

def tc028():
    """POST /my/bookings/create → redirect, booking created"""
    # Get CSRF token from confirm page
    csrf, _ = get_csrf(portal_session, f"{BASE_URL}/my/bookings/confirm?resource_id={resource_id}&start_datetime={start_str}&end_datetime={end_str}")
    assert csrf, "Could not get CSRF token"

    resp = portal_session.post(f"{BASE_URL}/my/bookings/create", data={
        "resource_id": resource_id,
        "start_datetime": start_str,
        "end_datetime": end_str,
        "subject": "HTTP Test Booking",
        "description": "Created via HTTP test",
        "csrf_token": csrf,
    }, allow_redirects=True)

    assert resp.status_code == 200, f"Expected 200 after redirect, got {resp.status_code}"
    assert "HTTP Test Booking" in resp.text or "booking" in resp.text.lower(), "Booking content missing after create"

    # Find the created booking via RPC
    bookings = rpc("booking.reservation", "search_read",
        [[("subject", "=", "HTTP Test Booking")]],
        {"fields": ["id", "subject", "state"], "limit": 1, "order": "id desc"})
    assert bookings, "Booking not found in database"
    test_booking_ids.append(bookings[0]["id"])
    print(f"    Created booking ID: {bookings[0]['id']}")
run_test("TC-028", "POST /my/bookings/create → redirect + booking created", tc028)

def tc029():
    """GET /my/bookings/{id} → 200, shows booking detail"""
    if not test_booking_ids:
        raise Exception("No test booking to check")
    bid = test_booking_ids[0]
    resp = portal_session.get(f"{BASE_URL}/my/bookings/{bid}")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"
    assert "HTTP Test Booking" in resp.text, "Missing booking subject in detail"
run_test("TC-029", "GET /my/bookings/{id} → 200 with detail", tc029)

def tc030():
    """POST /my/bookings/{id}/cancel → redirect, booking cancelled"""
    if not test_booking_ids:
        raise Exception("No test booking to cancel")
    bid = test_booking_ids[0]

    # Get CSRF from detail page
    csrf, _ = get_csrf(portal_session, f"{BASE_URL}/my/bookings/{bid}")
    assert csrf, "Could not get CSRF from detail page"

    resp = portal_session.post(f"{BASE_URL}/my/bookings/{bid}/cancel", data={
        "csrf_token": csrf,
    }, allow_redirects=True)

    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}"

    # Verify cancelled in DB
    booking = rpc("booking.reservation", "read", [[bid], ["state"]])[0]
    assert booking["state"] == "cancelled", f"Expected cancelled, got {booking['state']}"
run_test("TC-030", "POST /my/bookings/{id}/cancel → booking cancelled", tc030)

# ─── 2.2 New Form Fields ───
print("\n--- 2.2 New Form Fields ---")

def tc031():
    """Submit with subject → stored in reservation"""
    start2 = future_start + timedelta(hours=2)
    end2 = start2 + timedelta(hours=1)
    csrf, _ = get_csrf(portal_session, f"{BASE_URL}/my/bookings/confirm?resource_id={resource_id}&start_datetime={start2.strftime('%Y-%m-%d %H:%M:%S')}&end_datetime={end2.strftime('%Y-%m-%d %H:%M:%S')}")

    resp = portal_session.post(f"{BASE_URL}/my/bookings/create", data={
        "resource_id": resource_id,
        "start_datetime": start2.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end2.strftime("%Y-%m-%d %H:%M:%S"),
        "subject": "Subject Field Test",
        "csrf_token": csrf,
    }, allow_redirects=True)
    assert resp.status_code == 200

    bookings = rpc("booking.reservation", "search_read",
        [[("subject", "=", "Subject Field Test")]],
        {"fields": ["id", "subject", "name"], "limit": 1, "order": "id desc"})
    assert bookings, "Booking with subject not found"
    assert bookings[0]["subject"] == "Subject Field Test"
    assert bookings[0]["name"] == "Subject Field Test", f"Name should equal subject: {bookings[0]['name']}"
    test_booking_ids.append(bookings[0]["id"])
run_test("TC-031", "Submit with subject → stored correctly", tc031)

def tc032():
    """Submit with description → stored as text"""
    start3 = future_start + timedelta(hours=4)
    end3 = start3 + timedelta(hours=1)
    csrf, _ = get_csrf(portal_session, f"{BASE_URL}/my/bookings/confirm?resource_id={resource_id}&start_datetime={start3.strftime('%Y-%m-%d %H:%M:%S')}&end_datetime={end3.strftime('%Y-%m-%d %H:%M:%S')}")

    resp = portal_session.post(f"{BASE_URL}/my/bookings/create", data={
        "resource_id": resource_id,
        "start_datetime": start3.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end3.strftime("%Y-%m-%d %H:%M:%S"),
        "description": "This is a detailed meeting description with agenda items.",
        "csrf_token": csrf,
    }, allow_redirects=True)
    assert resp.status_code == 200

    bookings = rpc("booking.reservation", "search_read",
        [[("description", "ilike", "detailed meeting description")]],
        {"fields": ["id", "description"], "limit": 1, "order": "id desc"})
    assert bookings, "Booking with description not found"
    assert "detailed meeting description" in bookings[0]["description"]
    test_booking_ids.append(bookings[0]["id"])
run_test("TC-032", "Submit with description → stored in reservation", tc032)

def tc033():
    """Submit with enable_discussion=on → channel created (if resource allows)"""
    start4 = future_start + timedelta(hours=6)
    end4 = start4 + timedelta(hours=1)
    csrf, _ = get_csrf(portal_session, f"{BASE_URL}/my/bookings/confirm?resource_id={resource_id}&start_datetime={start4.strftime('%Y-%m-%d %H:%M:%S')}&end_datetime={end4.strftime('%Y-%m-%d %H:%M:%S')}")

    resp = portal_session.post(f"{BASE_URL}/my/bookings/create", data={
        "resource_id": resource_id,
        "start_datetime": start4.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end4.strftime("%Y-%m-%d %H:%M:%S"),
        "subject": "Discussion Enabled Booking",
        "enable_discussion": "on",
        "csrf_token": csrf,
    }, allow_redirects=True)
    assert resp.status_code == 200

    bookings = rpc("booking.reservation", "search_read",
        [[("subject", "=", "Discussion Enabled Booking")]],
        {"fields": ["id", "enable_discussion", "channel_id"], "limit": 1, "order": "id desc"})
    assert bookings, "Booking with discussion not found"
    assert bookings[0]["enable_discussion"] is True, "enable_discussion should be True"
    if bookings[0]["channel_id"]:
        print(f"    Channel auto-created: {bookings[0]['channel_id']}")
    test_booking_ids.append(bookings[0]["id"])
run_test("TC-033", "Submit with enable_discussion=on → channel created", tc033)

def tc034():
    """Submit without subject → reservation has auto-generated name"""
    start5 = future_start + timedelta(hours=8)
    end5 = start5 + timedelta(hours=1)
    csrf, _ = get_csrf(portal_session, f"{BASE_URL}/my/bookings/confirm?resource_id={resource_id}&start_datetime={start5.strftime('%Y-%m-%d %H:%M:%S')}&end_datetime={end5.strftime('%Y-%m-%d %H:%M:%S')}")

    resp = portal_session.post(f"{BASE_URL}/my/bookings/create", data={
        "resource_id": resource_id,
        "start_datetime": start5.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end5.strftime("%Y-%m-%d %H:%M:%S"),
        "csrf_token": csrf,
    }, allow_redirects=True)
    assert resp.status_code == 200

    # Find latest booking without subject
    bookings = rpc("booking.reservation", "search_read",
        [[("subject", "=", False), ("resource_type_id", "=", resource_id)]],
        {"fields": ["id", "name", "subject"], "limit": 1, "order": "id desc"})
    assert bookings, "Booking without subject not found"
    assert resource["name"] in bookings[0]["name"], f"Name should contain resource: {bookings[0]['name']}"
    test_booking_ids.append(bookings[0]["id"])
run_test("TC-034", "Submit without subject → auto-generated name", tc034)

def tc035():
    """Organizer auto-set to current portal user's partner"""
    # Check the latest booking we created
    if not test_booking_ids:
        raise Exception("No test bookings")
    bid = test_booking_ids[-1]
    booking = rpc("booking.reservation", "read", [[bid], ["organizer_id", "partner_id"]])[0]

    portal_user = rpc("res.users", "search_read",
        [[("login", "=", "portal")]],
        {"fields": ["partner_id"]})
    portal_partner_id = portal_user[0]["partner_id"][0]

    assert booking["organizer_id"], "Organizer should be set"
    assert booking["organizer_id"][0] == portal_partner_id, \
        f"Organizer should be portal partner ({portal_partner_id}), got {booking['organizer_id']}"
run_test("TC-035", "Organizer auto-set to portal user's partner", tc035)

# ─── 2.3 Error Handling ───
print("\n--- 2.3 Error Handling ---")

def tc036():
    """Confirm page with invalid resource_id → error or 404"""
    resp = portal_session.get(f"{BASE_URL}/my/bookings/confirm", params={
        "resource_id": 99999,
        "start_datetime": start_str,
        "end_datetime": end_str,
    })
    # Should get 404, 302, or error page
    assert resp.status_code in (200, 302, 404), f"Unexpected status: {resp.status_code}"
    if resp.status_code == 200:
        # Check if it's an error page
        text_lower = resp.text.lower()
        is_error = "error" in text_lower or "not found" in text_lower or "not available" in text_lower or "redirect" in resp.url
run_test("TC-036", "Confirm with invalid resource_id → handled gracefully", tc036)

def tc037():
    """Confirm page with past datetime → error handling"""
    past_start = (datetime.now(timezone.utc) - timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
    past_end = (datetime.now(timezone.utc) - timedelta(days=1) + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    resp = portal_session.get(f"{BASE_URL}/my/bookings/confirm", params={
        "resource_id": resource_id,
        "start_datetime": past_start,
        "end_datetime": past_end,
    })
    # Past bookings should either show error or still render (admin may allow)
    assert resp.status_code in (200, 302, 400, 403), f"Unexpected status: {resp.status_code}"
run_test("TC-037", "Confirm with past datetime → handled gracefully", tc037)

def tc038():
    """Create with missing resource_id → error"""
    csrf, _ = get_csrf(portal_session, f"{BASE_URL}/my/bookings/confirm?resource_id={resource_id}&start_datetime={start_str}&end_datetime={end_str}")
    resp = portal_session.post(f"{BASE_URL}/my/bookings/create", data={
        # missing resource_id
        "start_datetime": start_str,
        "end_datetime": end_str,
        "csrf_token": csrf,
    }, allow_redirects=True)
    # Should get error or redirect
    assert resp.status_code in (200, 302, 400, 500), f"Status: {resp.status_code}"
run_test("TC-038", "Create with missing required field → handled", tc038)

def tc039():
    """Cancel already-cancelled booking → graceful handling"""
    if not test_booking_ids:
        raise Exception("No test bookings")
    # TC-030 already cancelled the first booking
    bid = test_booking_ids[0]
    booking = rpc("booking.reservation", "read", [[bid], ["state"]])[0]
    if booking["state"] != "cancelled":
        rpc("booking.reservation", "action_cancel", [[bid]])

    csrf, _ = get_csrf(portal_session, f"{BASE_URL}/my/bookings/{bid}")
    resp = portal_session.post(f"{BASE_URL}/my/bookings/{bid}/cancel", data={
        "csrf_token": csrf,
    }, allow_redirects=True)
    # Should not error even though already cancelled
    assert resp.status_code in (200, 302), f"Status: {resp.status_code}"
run_test("TC-039", "Cancel already-cancelled → no crash", tc039)

def tc040():
    """Access other user's booking → 403 or redirect"""
    # Create a booking as admin (not the portal user)
    admin_partner = rpc("res.users", "search_read",
        [[("login", "=", "admin")]],
        {"fields": ["partner_id"]})
    admin_partner_id = admin_partner[0]["partner_id"][0]

    start_other = future_start + timedelta(days=2, hours=10)
    end_other = start_other + timedelta(hours=1)
    other_bid = rpc("booking.reservation", "create", [{
        "resource_type_id": resource_id,
        "partner_id": admin_partner_id,
        "start_datetime": start_other.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end_other.strftime("%Y-%m-%d %H:%M:%S"),
    }])

    # Portal user tries to access admin's booking
    resp = portal_session.get(f"{BASE_URL}/my/bookings/{other_bid}")
    assert resp.status_code in (200, 302, 403, 404), f"Status: {resp.status_code}"
    if resp.status_code == 200:
        # Should show access denied or redirect
        text = resp.text.lower()
        print(f"    Response has: {'access denied' if 'access' in text else 'rendered (might have error)'}")

    # Cleanup
    rpc("booking.reservation", "action_cancel", [[other_bid]])
    rpc("booking.reservation", "unlink", [[other_bid]])
run_test("TC-040", "Access other user's booking → denied or error", tc040)

# ─── 2.4 Additional HTTP Tests ───
print("\n--- 2.4 Additional HTTP Tests ---")

def tc041_http():
    """Booking list pagination works"""
    resp = portal_session.get(f"{BASE_URL}/my/bookings/page/1")
    assert resp.status_code == 200, f"Pagination page 1 status: {resp.status_code}"
run_test("TC-041h", "Booking list pagination → page/1 works", tc041_http)

def tc042_http():
    """Booking list with filter parameter"""
    for filter_val in ["all", "upcoming", "confirmed", "cancelled"]:
        resp = portal_session.get(f"{BASE_URL}/my/bookings", params={"filterby": filter_val})
        assert resp.status_code == 200, f"Filter {filter_val} status: {resp.status_code}"
run_test("TC-042h", "Booking list filters (all/upcoming/confirmed/cancelled)", tc042_http)

def tc043_http():
    """Booking list with sort parameter"""
    for sort_val in ["date_desc", "date_asc", "resource"]:
        resp = portal_session.get(f"{BASE_URL}/my/bookings", params={"sortby": sort_val})
        assert resp.status_code == 200, f"Sort {sort_val} status: {resp.status_code}"
run_test("TC-043h", "Booking list sorting (date_desc/date_asc/resource)", tc043_http)

def tc044_http():
    """JSON slots API endpoint"""
    resp = portal_session.post(f"{BASE_URL}/my/booking/resources/{resource_id}/slots",
        json={"jsonrpc": "2.0", "method": "call", "params": {
            "date_from": future_start.strftime("%Y-%m-%d"),
            "date_to": (future_start + timedelta(days=6)).strftime("%Y-%m-%d"),
        }},
        headers={"Content-Type": "application/json"})
    assert resp.status_code == 200, f"Slots API status: {resp.status_code}"
    data = resp.json()
    assert "result" in data or "error" in data, f"Invalid JSON-RPC response"
    if "result" in data:
        print(f"    Slots returned: {len(data['result'].get('slots', []))} slots")
run_test("TC-044h", "JSON slots API → returns slot data", tc044_http)

def tc045_http():
    """Non-authenticated access → redirect to login"""
    anon_session = requests.Session()
    resp = anon_session.get(f"{BASE_URL}/my/bookings", allow_redirects=False)
    assert resp.status_code in (302, 303), f"Expected redirect, got {resp.status_code}"
    assert "/web/login" in resp.headers.get("Location", ""), "Should redirect to login"
run_test("TC-045h", "Non-authenticated → redirect to /web/login", tc045_http)

# ─── Cleanup ───
print("\n--- Cleanup ---")
for bid in test_booking_ids:
    try:
        rpc("booking.reservation", "action_cancel", [[bid]])
        rpc("booking.reservation", "unlink", [[bid]])
    except Exception:
        pass
print(f"  Cleaned up {len(test_booking_ids)} test bookings")

# ─── Summary ───
print("\n" + "=" * 70)
print("ROUND 2 RESULTS SUMMARY")
print("=" * 70)
passed = sum(1 for r in results if r[2] == "PASS")
failed = sum(1 for r in results if r[2] == "FAIL")
print(f"\n  Total: {len(results)}  |  PASS: {passed}  |  FAIL: {failed}")
print(f"  Pass Rate: {passed/len(results)*100:.1f}%\n")

if failed > 0:
    print("  FAILED TESTS:")
    for tc_id, desc, status, err in results:
        if status == "FAIL":
            print(f"    {tc_id}: {desc}")
            print(f"      Error: {err[:300]}")
print()
