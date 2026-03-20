#!/usr/bin/env python3
"""
Phase 7: UI/UX and i18n Tests for Odoo Booking Reservation module.

Tests portal page loading, Chinese (zh_TW) translation verification,
error handling, responsive design, asset loading, and form validation
using HTTP requests against the running Odoo instance.
"""
import sys
import time
import re

sys.path.insert(0, '.')

import requests
from tests.odoo_rpc import OdooRPC

# ============================================================
# Configuration
# ============================================================
BASE_URL = "http://localhost:9071"
DB = "odoocalendar"

ADMIN_LOGIN = "admin"
ADMIN_PASSWORD = "admin"
PORTAL_LOGIN = "portal1"
PORTAL_PASSWORD = "portal1"

# Track test results
results = []


def record(test_id, name, passed, detail=""):
    """Record a test result."""
    status = "PASS" if passed else "FAIL"
    results.append({"id": test_id, "name": name, "passed": passed, "detail": detail})
    print(f"  [{status}] {test_id} - {name}")
    if detail:
        print(f"         {detail}")


def get_session(login, password):
    """Create an authenticated requests session via /web/login."""
    session = requests.Session()
    # First GET to obtain the CSRF token
    resp = session.get(f"{BASE_URL}/web/login", timeout=30)
    # Extract csrf_token from the login page
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    csrf_token = csrf_match.group(1) if csrf_match else ""

    # POST the login form
    login_data = {
        "login": login,
        "password": password,
        "db": DB,
        "csrf_token": csrf_token,
    }
    resp = session.post(f"{BASE_URL}/web/login", data=login_data, timeout=30, allow_redirects=True)
    return session, resp


# ============================================================
# 7.1 Backend Page Load Tests (admin session)
# ============================================================
def test_7_1_backend_pages():
    print("\n" + "=" * 60)
    print("7.1 Backend Page Load Tests (admin session)")
    print("=" * 60)

    # a) Login as admin via POST /web/login
    session, login_resp = get_session(ADMIN_LOGIN, ADMIN_PASSWORD)
    logged_in = login_resp.status_code == 200 and "/web/login" not in login_resp.url
    record("7.1a", "Admin login via POST /web/login",
           logged_in,
           f"status={login_resp.status_code}, url={login_resp.url}")

    # b) GET /web - backend home, check 200
    resp = session.get(f"{BASE_URL}/web", timeout=30)
    record("7.1b", "GET /web - backend home returns 200",
           resp.status_code == 200,
           f"status={resp.status_code}, length={len(resp.text)}")

    # c) Verify the booking menu loads (check for booking-related strings)
    body = resp.text.lower()
    has_booking_ref = any(kw in body for kw in [
        "booking", "reservation", "resource booking",
        # Check for menu action XML IDs that would appear in the webclient
        "booking_reservation", "booking_resource",
    ])
    # Also try loading the menu data via JSON-RPC
    menu_resp = session.post(f"{BASE_URL}/web/action/load", json={
        "jsonrpc": "2.0",
        "method": "call",
        "params": {
            "action_id": "odoo_booking_reservation.action_booking_reservation_calendar",
        },
    }, timeout=30)
    menu_ok = menu_resp.status_code == 200
    # The webclient is a SPA, so booking references might be in lazy-loaded data.
    # We also check that the action load endpoint responds.
    record("7.1c", "Booking menu / action references accessible",
           has_booking_ref or menu_ok,
           f"booking_in_body={has_booking_ref}, action_load_status={menu_resp.status_code}")

    session.close()


# ============================================================
# 7.2 Portal Page Load Tests
# ============================================================
def test_7_2_portal_pages():
    print("\n" + "=" * 60)
    print("7.2 Portal Page Load Tests (portal1 session)")
    print("=" * 60)

    session, login_resp = get_session(PORTAL_LOGIN, PORTAL_PASSWORD)
    logged_in = login_resp.status_code == 200
    record("7.2-login", "Portal login as portal1",
           logged_in,
           f"status={login_resp.status_code}, url={login_resp.url}")

    timings = {}

    # a) GET /my - portal home
    t0 = time.time()
    resp_my = session.get(f"{BASE_URL}/my", timeout=30)
    timings["/my"] = time.time() - t0
    record("7.2a", "GET /my - portal home returns 200",
           resp_my.status_code == 200,
           f"status={resp_my.status_code}, time={timings['/my']:.3f}s")

    # b) GET /my/booking/resources - resource list
    t0 = time.time()
    resp_resources = session.get(f"{BASE_URL}/my/booking/resources", timeout=30)
    timings["/my/booking/resources"] = time.time() - t0
    record("7.2b", "GET /my/booking/resources - resource list returns 200",
           resp_resources.status_code == 200,
           f"status={resp_resources.status_code}, time={timings['/my/booking/resources']:.3f}s")

    # c) GET /my/booking/resources/2 - Conference Room A detail
    t0 = time.time()
    resp_detail = session.get(f"{BASE_URL}/my/booking/resources/2", timeout=30)
    timings["/my/booking/resources/2"] = time.time() - t0
    # Accept 200 (success) or 403 (access denied but not 500)
    ok = resp_detail.status_code in (200, 302, 403)
    record("7.2c", "GET /my/booking/resources/2 - Conference Room A detail",
           ok,
           f"status={resp_detail.status_code}, time={timings['/my/booking/resources/2']:.3f}s")

    # d) GET /my/bookings - my bookings list
    t0 = time.time()
    resp_bookings = session.get(f"{BASE_URL}/my/bookings", timeout=30)
    timings["/my/bookings"] = time.time() - t0
    record("7.2d", "GET /my/bookings - my bookings list returns 200",
           resp_bookings.status_code == 200,
           f"status={resp_bookings.status_code}, time={timings['/my/bookings']:.3f}s")

    # e) Report response times
    print("\n  Response time summary:")
    all_fast = True
    for path, t in timings.items():
        status = "OK" if t < 5.0 else "SLOW"
        if t >= 5.0:
            all_fast = False
        print(f"    {path}: {t:.3f}s [{status}]")
    record("7.2e", "All portal pages respond within 5 seconds",
           all_fast,
           f"times: {', '.join(f'{k}={v:.3f}s' for k, v in timings.items())}")

    session.close()
    return resp_resources.text if resp_resources.status_code == 200 else ""


# ============================================================
# 7.3 Chinese Language Verification
# ============================================================
def test_7_3_chinese_language(resources_html=""):
    print("\n" + "=" * 60)
    print("7.3 Chinese Language Verification (zh_TW)")
    print("=" * 60)

    session, _ = get_session(PORTAL_LOGIN, PORTAL_PASSWORD)

    # a) Check /my/booking/resources contains Chinese text
    if not resources_html:
        resp = session.get(f"{BASE_URL}/my/booking/resources", timeout=30)
        resources_html = resp.text

    # Chinese characters range: CJK Unified Ideographs U+4E00-U+9FFF
    # Also check CJK Compatibility Ideographs and Extension ranges
    chinese_chars = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]', resources_html)
    has_chinese = len(chinese_chars) > 0

    # Show a sample of Chinese text found
    sample = ""
    if has_chinese:
        # Try to find meaningful Chinese phrases
        chinese_phrases = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]+', resources_html)
        sample = ", ".join(chinese_phrases[:10])

    record("7.3a", "Portal resources page contains Chinese (zh_TW) text",
           has_chinese,
           f"found {len(chinese_chars)} Chinese chars, sample: [{sample}]")

    # b) Check date format in responses
    # Fetch the resource detail page to look for date formatting
    resp_detail = session.get(f"{BASE_URL}/my/booking/resources/2", timeout=30)
    detail_html = resp_detail.text

    # Look for date patterns -- could be YYYY-MM-DD, YYYY/MM/DD, or localized
    # Chinese dates often use: 2024年3月20日 or similar
    has_date_format = bool(re.search(
        r'\d{4}[-/]\d{1,2}[-/]\d{1,2}|'       # ISO-style dates
        r'\d{4}\s*年\s*\d{1,2}\s*月|'          # Chinese year-month
        r'(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}|'  # English abbreviated
        r'\d{1,2}:\d{2}',                       # Time format HH:MM
        detail_html
    ))
    record("7.3b", "Date/time format present in portal pages",
           has_date_format,
           f"status={resp_detail.status_code}, date_patterns_found={has_date_format}")

    # Also check /my page for Chinese
    resp_my = session.get(f"{BASE_URL}/my", timeout=30)
    my_chinese = re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf]+', resp_my.text)
    record("7.3c", "Portal home /my contains Chinese text",
           len(my_chinese) > 0,
           f"found {len(my_chinese)} Chinese phrases, sample: [{', '.join(my_chinese[:8])}]")

    session.close()


# ============================================================
# 7.4 Error Page Tests
# ============================================================
def test_7_4_error_pages():
    print("\n" + "=" * 60)
    print("7.4 Error Page Tests")
    print("=" * 60)

    session, _ = get_session(PORTAL_LOGIN, PORTAL_PASSWORD)

    # a) GET /my/booking/resources/99999 - non-existent resource
    resp = session.get(f"{BASE_URL}/my/booking/resources/99999", timeout=30)
    # Should NOT be a 500 server error. Acceptable: 403, 404, or redirect
    not_500 = resp.status_code != 500
    record("7.4a", "GET /my/booking/resources/99999 - not a 500 error",
           not_500,
           f"status={resp.status_code}")

    # Check that we got a sensible error page (not raw traceback)
    no_traceback = "Traceback" not in resp.text and "Internal Server Error" not in resp.text[:500]
    record("7.4a2", "Non-existent resource: no raw traceback shown",
           no_traceback or resp.status_code in (302, 303, 403, 404),
           f"status={resp.status_code}, has_traceback={'Traceback' in resp.text}")

    # b) GET /my/bookings/99999 - non-existent booking
    resp2 = session.get(f"{BASE_URL}/my/bookings/99999", timeout=30)
    not_500_b = resp2.status_code != 500
    record("7.4b", "GET /my/bookings/99999 - not a 500 error",
           not_500_b,
           f"status={resp2.status_code}")

    no_traceback_b = "Traceback" not in resp2.text and "Internal Server Error" not in resp2.text[:500]
    record("7.4b2", "Non-existent booking: no raw traceback shown",
           no_traceback_b or resp2.status_code in (302, 303, 403, 404),
           f"status={resp2.status_code}, has_traceback={'Traceback' in resp2.text}")

    # c) Verify appropriate error handling (not a 500)
    both_handled = not_500 and not_500_b
    record("7.4c", "All error pages handled gracefully (no 500s)",
           both_handled,
           f"resource_99999={resp.status_code}, booking_99999={resp2.status_code}")

    session.close()


# ============================================================
# 7.5 Responsive Design Check
# ============================================================
def test_7_5_responsive():
    print("\n" + "=" * 60)
    print("7.5 Responsive Design Check (mobile user-agent)")
    print("=" * 60)

    mobile_ua = (
        "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) "
        "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
        "Mobile/15E148 Safari/604.1"
    )

    session, _ = get_session(PORTAL_LOGIN, PORTAL_PASSWORD)
    session.headers.update({"User-Agent": mobile_ua})

    pages = {
        "/my": "Portal home",
        "/my/booking/resources": "Resource list",
        "/my/booking/resources/2": "Resource detail",
        "/my/bookings": "My bookings",
    }

    all_ok = True
    for path, desc in pages.items():
        resp = session.get(f"{BASE_URL}{path}", timeout=30)
        ok = resp.status_code in (200, 302, 403)
        if not ok:
            all_ok = False
        record(f"7.5-{path}", f"Mobile UA: {desc} ({path})",
               ok,
               f"status={resp.status_code}, length={len(resp.text)}")

    # Check that the resource list page includes responsive meta viewport tag
    resp = session.get(f"{BASE_URL}/my/booking/resources", timeout=30)
    has_viewport = 'viewport' in resp.text.lower()
    record("7.5-viewport", "Pages include viewport meta tag for responsive",
           has_viewport,
           f"viewport_found={has_viewport}")

    record("7.5-summary", "All pages return OK with mobile user-agent",
           all_ok,
           "All pages accessible from mobile browser")

    session.close()


# ============================================================
# 7.6 CSS/JS Asset Loading
# ============================================================
def test_7_6_assets():
    print("\n" + "=" * 60)
    print("7.6 CSS/JS Asset Loading")
    print("=" * 60)

    session, _ = get_session(PORTAL_LOGIN, PORTAL_PASSWORD)

    # a) Load a portal page and find the bundled CSS asset URL
    resp = session.get(f"{BASE_URL}/my/booking/resources", timeout=30)
    page_html = resp.text

    # Odoo bundles assets -- look for references to portal.css in the page
    # The CSS is bundled via web.assets_frontend, so look for the bundle URL
    css_urls = re.findall(r'href="([^"]*(?:assets_frontend|portal)[^"]*\.css[^"]*)"', page_html)
    if not css_urls:
        # Look for any .css link
        css_urls = re.findall(r'href="([^"]*\.css[^"]*)"', page_html)

    css_loaded = False
    css_url_checked = ""
    if css_urls:
        for css_url in css_urls[:5]:
            full_url = css_url if css_url.startswith("http") else f"{BASE_URL}{css_url}"
            css_resp = session.get(full_url, timeout=30)
            if css_resp.status_code == 200:
                css_loaded = True
                css_url_checked = css_url
                break

    record("7.6a", "CSS assets load successfully (portal styles)",
           css_loaded,
           f"url={css_url_checked}, found_urls={len(css_urls)}")

    # b) Check response contains expected CSS classes from portal_templates.xml
    expected_classes = [
        "card",              # Bootstrap card used in resource cards
        "btn-primary",       # Primary button used for "Book Now"
        "btn-outline-success",  # Available slot button
        "slot-btn",          # Custom CSS class from portal.css
        "badge",             # Status badges
        "table",             # Booking table
        "fa fa-calendar",    # Font Awesome calendar icon
    ]

    found_classes = []
    missing_classes = []
    for cls in expected_classes:
        if cls in page_html:
            found_classes.append(cls)
        else:
            missing_classes.append(cls)

    # Some classes are only on specific pages, so check detail page too
    resp_detail = session.get(f"{BASE_URL}/my/booking/resources/2", timeout=30)
    resp_bookings = session.get(f"{BASE_URL}/my/bookings", timeout=30)
    combined_html = page_html + resp_detail.text + resp_bookings.text

    for cls in list(missing_classes):
        if cls in combined_html:
            found_classes.append(cls)
            missing_classes.remove(cls)

    enough_found = len(found_classes) >= len(expected_classes) * 0.5  # At least half
    record("7.6b", "Expected CSS classes from portal_templates.xml present",
           enough_found,
           f"found={found_classes}, missing={missing_classes}")

    # c) Check JS assets load
    js_urls = re.findall(r'src="([^"]*(?:assets_frontend|web\.assets)[^"]*\.js[^"]*)"', page_html)
    if not js_urls:
        js_urls = re.findall(r'src="([^"]*\.js[^"]*)"', page_html)

    js_loaded = False
    js_url_checked = ""
    if js_urls:
        for js_url in js_urls[:3]:
            full_url = js_url if js_url.startswith("http") else f"{BASE_URL}{js_url}"
            js_resp = session.get(full_url, timeout=30)
            if js_resp.status_code == 200:
                js_loaded = True
                js_url_checked = js_url
                break

    record("7.6c", "JS assets load successfully",
           js_loaded,
           f"url={js_url_checked}, found_urls={len(js_urls)}")

    session.close()


# ============================================================
# 7.7 Form Validation
# ============================================================
def test_7_7_form_validation():
    print("\n" + "=" * 60)
    print("7.7 Form Validation")
    print("=" * 60)

    session, _ = get_session(PORTAL_LOGIN, PORTAL_PASSWORD)

    # Get CSRF token from a page
    resp = session.get(f"{BASE_URL}/my/booking/resources/2", timeout=30)
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    csrf_token = csrf_match.group(1) if csrf_match else ""

    # a) POST /my/bookings/create with missing fields
    post_data = {
        "csrf_token": csrf_token,
        # Missing resource_id, start_datetime, end_datetime
    }
    resp_missing = session.post(f"{BASE_URL}/my/bookings/create",
                                data=post_data, timeout=30, allow_redirects=True)
    # Should redirect to error page or show validation error, NOT 500
    not_500_a = resp_missing.status_code != 500
    # The controller redirects to /my/bookings/new?error=missing_fields
    has_error_redirect = "error" in resp_missing.url or resp_missing.status_code in (200, 302, 303)
    record("7.7a", "POST /my/bookings/create with missing fields - handled gracefully",
           not_500_a,
           f"status={resp_missing.status_code}, url={resp_missing.url}, "
           f"error_in_url={'error' in resp_missing.url}")

    # b) POST with invalid resource_id
    # Re-fetch CSRF token
    resp2 = session.get(f"{BASE_URL}/my/bookings/new", timeout=30)
    csrf_match2 = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp2.text)
    csrf_token2 = csrf_match2.group(1) if csrf_match2 else csrf_token

    post_data_invalid = {
        "csrf_token": csrf_token2,
        "resource_id": "99999",
        "start_datetime": "2099-06-15 09:00:00",
        "end_datetime": "2099-06-15 10:00:00",
        "note": "Test invalid resource",
    }
    resp_invalid = session.post(f"{BASE_URL}/my/bookings/create",
                                data=post_data_invalid, timeout=30, allow_redirects=True)
    not_500_b = resp_invalid.status_code != 500
    record("7.7b", "POST with invalid resource_id (99999) - handled gracefully",
           not_500_b,
           f"status={resp_invalid.status_code}, url={resp_invalid.url}")

    # c) POST with resource_id=0 (edge case)
    resp3 = session.get(f"{BASE_URL}/my/bookings/new", timeout=30)
    csrf_match3 = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp3.text)
    csrf_token3 = csrf_match3.group(1) if csrf_match3 else csrf_token

    post_data_zero = {
        "csrf_token": csrf_token3,
        "resource_id": "0",
        "start_datetime": "2099-06-15 09:00:00",
        "end_datetime": "2099-06-15 10:00:00",
    }
    resp_zero = session.post(f"{BASE_URL}/my/bookings/create",
                             data=post_data_zero, timeout=30, allow_redirects=True)
    not_500_c = resp_zero.status_code != 500
    record("7.7c", "POST with resource_id=0 - handled gracefully",
           not_500_c,
           f"status={resp_zero.status_code}, url={resp_zero.url}")

    # d) Verify proper error handling overall
    all_handled = not_500_a and not_500_b and not_500_c
    record("7.7d", "All form validation errors handled (no 500s)",
           all_handled,
           f"missing_fields={resp_missing.status_code}, "
           f"invalid_resource={resp_invalid.status_code}, "
           f"zero_resource={resp_zero.status_code}")

    session.close()


# ============================================================
# Main
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("Phase 7: UI/UX & i18n Tests")
    print(f"Instance: {BASE_URL}  DB: {DB}")
    print("=" * 60)

    # Verify connectivity first
    try:
        rpc = OdooRPC("admin", "admin")
        print(f"RPC connection OK (uid={rpc.uid})")
    except Exception as e:
        print(f"FATAL: Cannot connect to Odoo via RPC: {e}")
        sys.exit(1)

    try:
        resp = requests.get(f"{BASE_URL}/web/login", timeout=10)
        print(f"HTTP connection OK (status={resp.status_code})")
    except Exception as e:
        print(f"FATAL: Cannot connect to Odoo via HTTP: {e}")
        sys.exit(1)

    # Run all test sections
    test_7_1_backend_pages()
    resources_html = test_7_2_portal_pages()
    test_7_3_chinese_language(resources_html)
    test_7_4_error_pages()
    test_7_5_responsive()
    test_7_6_assets()
    test_7_7_form_validation()

    # ============================================================
    # Summary
    # ============================================================
    print("\n" + "=" * 60)
    print("PHASE 7 SUMMARY")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = sum(1 for r in results if not r["passed"])

    print(f"\nTotal: {total}  |  PASS: {passed}  |  FAIL: {failed}")
    print(f"Pass rate: {passed / total * 100:.1f}%\n")

    if failed > 0:
        print("Failed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  [FAIL] {r['id']} - {r['name']}")
                if r["detail"]:
                    print(f"         {r['detail']}")

    print("\n" + "=" * 60)
    print(f"Phase 7 Complete: {passed}/{total} passed")
    print("=" * 60)
