#!/usr/bin/env python3
"""
Regression test: verify all 5 previously failed tests now pass after bug fixes.

BUG-001 fixes (ir.rule):
  - D3a: portal1 should NOT be able to read portal2's reservation via RPC
  - D3b: portal1 should NOT be able to write portal2's reservation via RPC
  - 6.4b: portal2 should NOT be able to write portal1's reservation via RPC

BUG-002 fix (resource existence check):
  - 7.7b: POST /my/bookings/create with resource_id=99999 should NOT return 500
  - 7.7d: All form validation errors handled (no 500s)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from odoo_rpc import OdooRPC
import requests
from datetime import datetime, timedelta

URL = "http://localhost:9071"
results = []

def record(test_id, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"id": test_id, "name": name, "passed": passed, "detail": detail})
    print(f"  [{status}] {test_id} - {name}")
    if detail:
        print(f"         {detail}")


def get_session(login, password):
    s = requests.Session()
    # Get CSRF token
    resp = s.get(f"{URL}/web/login")
    import re
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    token = csrf.group(1) if csrf else ""
    # Login
    s.post(f"{URL}/web/login", data={
        "login": login,
        "password": password,
        "csrf_token": token,
        "redirect": "/my",
    })
    return s, token


def test_bug001_portal_isolation():
    """Test BUG-001: Portal users can only access their own reservations via RPC."""
    print("\n" + "=" * 60)
    print("BUG-001 Regression: Portal reservation isolation (ir.rule)")
    print("=" * 60)

    rpc_admin = OdooRPC("admin", "admin")
    rpc_portal1 = OdooRPC("portal1", "portal1")
    rpc_portal2 = OdooRPC("portal2", "portal2")

    # Get partner IDs
    p1_partner = rpc_admin.read("res.users", [rpc_portal1.uid], ["partner_id"])[0]["partner_id"][0]
    p2_partner = rpc_admin.read("res.users", [rpc_portal2.uid], ["partner_id"])[0]["partner_id"][0]

    # Create reservations as admin (sudo) for each portal user
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    res1_id = rpc_admin.create("booking.reservation", {
        "resource_type_id": 2,
        "start_datetime": f"{tomorrow} 08:00:00",
        "end_datetime": f"{tomorrow} 09:00:00",
        "partner_id": p1_partner,
        "note": "regression_test_portal1",
        "state": "confirmed",
    })
    res2_id = rpc_admin.create("booking.reservation", {
        "resource_type_id": 3,
        "start_datetime": f"{tomorrow} 08:00:00",
        "end_datetime": f"{tomorrow} 08:30:00",
        "partner_id": p2_partner,
        "note": "regression_test_portal2",
        "state": "confirmed",
    })
    print(f"  Created: portal1 reservation={res1_id}, portal2 reservation={res2_id}")

    # D3a: portal1 tries to read portal2's reservation
    try:
        data = rpc_portal1.read("booking.reservation", [res2_id], ["partner_id", "note"])
        # If we get here and data has content, it means portal1 CAN read portal2's data = FAIL
        if data and data[0].get("id") == res2_id:
            record("D3a", "portal1 CANNOT read portal2's reservation via RPC",
                   False, f"Still readable: partner_id={data[0].get('partner_id')}")
        else:
            record("D3a", "portal1 CANNOT read portal2's reservation via RPC",
                   True, "Read returned empty or filtered result")
    except Exception as e:
        # AccessError = correctly blocked
        record("D3a", "portal1 CANNOT read portal2's reservation via RPC",
               True, f"Blocked: {type(e).__name__}")

    # D3b: portal1 tries to write portal2's reservation
    try:
        rpc_portal1.write("booking.reservation", [res2_id], {"note": "hacked_by_portal1"})
        # Verify if write actually happened
        check = rpc_admin.read("booking.reservation", [res2_id], ["note"])[0]
        if check["note"] == "hacked_by_portal1":
            record("D3b", "portal1 CANNOT write portal2's reservation via RPC",
                   False, "Write succeeded - still vulnerable!")
        else:
            record("D3b", "portal1 CANNOT write portal2's reservation via RPC",
                   True, "Write appeared to succeed but data unchanged")
    except Exception as e:
        record("D3b", "portal1 CANNOT write portal2's reservation via RPC",
               True, f"Blocked: {type(e).__name__}")

    # 6.4b: portal2 tries to write portal1's reservation
    try:
        rpc_portal2.write("booking.reservation", [res1_id], {"note": "hacked_by_portal2"})
        check = rpc_admin.read("booking.reservation", [res1_id], ["note"])[0]
        if check["note"] == "hacked_by_portal2":
            record("6.4b", "portal2 CANNOT write portal1's reservation via RPC",
                   False, "Write succeeded - still vulnerable!")
        else:
            record("6.4b", "portal2 CANNOT write portal1's reservation via RPC",
                   True, "Write appeared to succeed but data unchanged")
    except Exception as e:
        record("6.4b", "portal2 CANNOT write portal1's reservation via RPC",
               True, f"Blocked: {type(e).__name__}")

    # Verify portal users CAN still access their OWN reservations
    try:
        own = rpc_portal1.read("booking.reservation", [res1_id], ["note"])
        record("D3-own", "portal1 CAN still read own reservation",
               bool(own and own[0].get("note") == "regression_test_portal1"),
               f"note={own[0].get('note') if own else 'N/A'}")
    except Exception as e:
        record("D3-own", "portal1 CAN still read own reservation",
               False, f"Error: {e}")

    # Cleanup
    try:
        rpc_admin.execute("booking.reservation", "unlink", [[res1_id, res2_id]])
    except:
        pass


def test_bug002_invalid_resource():
    """Test BUG-002: POST with invalid resource_id should not return 500."""
    print("\n" + "=" * 60)
    print("BUG-002 Regression: Invalid resource_id in portal create")
    print("=" * 60)

    session, _ = get_session("portal1", "portal1")

    # Get fresh CSRF token from bookings/new page
    import re
    resp = session.get(f"{URL}/my/bookings/new")
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    token = csrf.group(1) if csrf else ""

    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    # 7.7b: POST with resource_id=99999 (non-existent)
    resp = session.post(f"{URL}/my/bookings/create", data={
        "resource_id": "99999",
        "start_datetime": f"{tomorrow} 10:00:00",
        "end_datetime": f"{tomorrow} 11:00:00",
        "note": "regression test",
        "csrf_token": token,
    }, allow_redirects=True)

    record("7.7b", "POST with invalid resource_id (99999) - handled gracefully",
           resp.status_code != 500,
           f"status={resp.status_code}, url={resp.url}")

    # 7.7d: Aggregate - all form validations should be non-500
    # Re-test missing fields too
    resp2 = session.post(f"{URL}/my/bookings/create", data={
        "csrf_token": token,
    }, allow_redirects=True)

    resp3 = session.post(f"{URL}/my/bookings/create", data={
        "resource_id": "0",
        "csrf_token": token,
    }, allow_redirects=True)

    all_ok = resp.status_code != 500 and resp2.status_code != 500 and resp3.status_code != 500
    record("7.7d", "All form validation errors handled (no 500s)",
           all_ok,
           f"invalid_resource={resp.status_code}, missing={resp2.status_code}, zero={resp3.status_code}")


if __name__ == "__main__":
    print("=" * 60)
    print("REGRESSION TEST: Verify fixes for 5 previously failed tests")
    print(f"Instance: {URL}  Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)

    test_bug001_portal_isolation()
    test_bug002_invalid_resource()

    # Summary
    print("\n" + "=" * 60)
    print("REGRESSION TEST SUMMARY")
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
    else:
        print("ALL PREVIOUSLY FAILED TESTS NOW PASS!")

    print("\n" + "=" * 60)
    print(f"Regression Test Complete: {passed}/{total} passed")
    print("=" * 60)

    sys.exit(0 if failed == 0 else 1)
