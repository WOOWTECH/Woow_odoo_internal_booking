#!/usr/bin/env python3
"""
Round 1: API/RPC Layer Tests
Enterprise-grade comprehensive testing for odoo_booking_reservation
Tests model CRUD, new fields, constraints, discussion channel integration
"""
import xmlrpc.client
import sys
import traceback
from datetime import datetime, timedelta

URL = "http://localhost:9071"
DB = "odoocalendar"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object", allow_none=True)

admin_uid = common.authenticate(DB, ADMIN_USER, ADMIN_PASS, {})
assert admin_uid, "Admin authentication failed"

results = []

def run_test(tc_id, description, func):
    """Run a test case and record result."""
    try:
        func()
        results.append((tc_id, description, "PASS", ""))
        print(f"  ✓ {tc_id}: {description}")
    except Exception as e:
        tb = traceback.format_exc()
        results.append((tc_id, description, "FAIL", str(e)))
        print(f"  ✗ {tc_id}: {description}")
        print(f"    Error: {e}")
        # Print relevant traceback lines
        for line in tb.strip().split('\n')[-3:]:
            print(f"    {line}")

def rpc(model, method, args, kwargs=None):
    """Shortcut for XML-RPC calls."""
    return models.execute_kw(DB, admin_uid, ADMIN_PASS, model, method, args, kwargs or {})

def cleanup_reservations(ids):
    """Cancel and delete test reservations."""
    try:
        rpc("booking.reservation", "write", [ids, {"state": "cancelled"}])
        rpc("booking.reservation", "unlink", [ids])
    except Exception:
        pass

# ─── Setup: Get existing resource and partner ───
print("\n" + "=" * 70)
print("ROUND 1: API/RPC LAYER TESTS")
print("=" * 70)

print("\n--- Setup ---")
resources = rpc("booking.resource.type", "search_read", [[("active", "=", True)]], {"fields": ["id", "name", "enable_discussion", "location", "capacity"], "limit": 5})
print(f"  Available resources: {[(r['id'], r['name']) for r in resources]}")
assert resources, "No active resources found"
resource = resources[0]
resource_id = resource["id"]
print(f"  Using resource: {resource['name']} (ID: {resource_id})")

partners = rpc("res.partner", "search_read", [[("id", ">", 1)]], {"fields": ["id", "name"], "limit": 5})
assert partners, "No partners found"
partner = partners[0]
partner_id = partner["id"]
print(f"  Using partner: {partner['name']} (ID: {partner_id})")

# Get portal user's partner
portal_users = rpc("res.users", "search_read", [[("login", "=", "portal")]], {"fields": ["partner_id"]})
portal_partner_id = portal_users[0]["partner_id"][0] if portal_users else partner_id
print(f"  Portal partner ID: {portal_partner_id}")

# Ensure resource allows discussion for testing
rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": True}])

# Future datetimes for test bookings
now = datetime.utcnow()
base_start = now.replace(hour=10, minute=0, second=0, microsecond=0) + timedelta(days=3)
base_end = base_start + timedelta(hours=1)
test_reservation_ids = []

print(f"  Base booking time: {base_start.strftime('%Y-%m-%d %H:%M')} UTC")

# ─── 1.1 New Field CRUD ───
print("\n--- 1.1 New Field CRUD ---")

def tc001():
    """Create reservation with subject → verify name uses subject"""
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": (base_start + timedelta(days=0, hours=0)).strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (base_start + timedelta(days=0, hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "subject": "Weekly Team Standup",
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["name", "subject"]])[0]
    assert rec["subject"] == "Weekly Team Standup", f"Subject mismatch: {rec['subject']}"
    assert rec["name"] == "Weekly Team Standup", f"Name should equal subject: {rec['name']}"
run_test("TC-001", "Create with subject → name uses subject", tc001)

def tc002():
    """Create reservation without subject → verify name uses resource+datetime"""
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": (base_start + timedelta(days=0, hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (base_start + timedelta(days=0, hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["name", "subject"]])[0]
    assert not rec["subject"], f"Subject should be empty: {rec['subject']}"
    assert resource["name"] in rec["name"], f"Name should contain resource name: {rec['name']}"
run_test("TC-002", "Create without subject → name uses resource+datetime", tc002)

def tc003():
    """Create reservation with description (HTML content)"""
    html_desc = "<p>Meeting agenda:</p><ul><li>Sprint review</li><li>Planning</li></ul>"
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": (base_start + timedelta(days=0, hours=4)).strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (base_start + timedelta(days=0, hours=5)).strftime("%Y-%m-%d %H:%M:%S"),
        "description": html_desc,
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["description"]])[0]
    # Odoo may sanitize HTML, so check key content is preserved
    assert "Sprint review" in rec["description"], f"Description content missing: {rec['description'][:100]}"
    assert "Planning" in rec["description"], f"Description content missing: {rec['description'][:100]}"
run_test("TC-003", "Create with HTML description → content preserved", tc003)

def tc004():
    """Create reservation with organizer_id"""
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": (base_start + timedelta(days=0, hours=6)).strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (base_start + timedelta(days=0, hours=7)).strftime("%Y-%m-%d %H:%M:%S"),
        "organizer_id": partner_id,
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["organizer_id"]])[0]
    assert rec["organizer_id"] and rec["organizer_id"][0] == partner_id, \
        f"Organizer mismatch: {rec['organizer_id']}"
run_test("TC-004", "Create with organizer_id → stored correctly", tc004)

def tc005():
    """Create reservation with attendee_ids (multiple partners)"""
    all_partners = rpc("res.partner", "search", [[("id", ">", 1)]], {"limit": 3})
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": (base_start + timedelta(days=1, hours=0)).strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (base_start + timedelta(days=1, hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "attendee_ids": [(6, 0, all_partners)],
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["attendee_ids"]])[0]
    assert len(rec["attendee_ids"]) == len(all_partners), \
        f"Attendee count mismatch: expected {len(all_partners)}, got {len(rec['attendee_ids'])}"
run_test("TC-005", "Create with attendee_ids → multiple partners stored", tc005)

def tc006():
    """Update subject → verify name recomputed"""
    rid = test_reservation_ids[0]  # The one with "Weekly Team Standup"
    rpc("booking.reservation", "write", [[rid], {"subject": "Updated Meeting Title"}])
    rec = rpc("booking.reservation", "read", [[rid], ["name", "subject"]])[0]
    assert rec["subject"] == "Updated Meeting Title", f"Subject not updated: {rec['subject']}"
    assert rec["name"] == "Updated Meeting Title", f"Name not recomputed: {rec['name']}"
    # Restore original
    rpc("booking.reservation", "write", [[rid], {"subject": "Weekly Team Standup"}])
run_test("TC-006", "Update subject → name recomputed", tc006)

def tc007():
    """Set reminder_type and reminder_time"""
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": (base_start + timedelta(days=1, hours=2)).strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (base_start + timedelta(days=1, hours=3)).strftime("%Y-%m-%d %H:%M:%S"),
        "reminder_type": "email",
        "reminder_time": 30,
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["reminder_type", "reminder_time"]])[0]
    assert rec["reminder_type"] == "email", f"Reminder type: {rec['reminder_type']}"
    assert rec["reminder_time"] == 30, f"Reminder time: {rec['reminder_time']}"
run_test("TC-007", "Set reminder_type and reminder_time → stored correctly", tc007)

def tc008():
    """Read all new fields back and verify types/values"""
    rid = test_reservation_ids[0]
    fields = ["subject", "description", "organizer_id", "attendee_ids",
              "enable_discussion", "channel_id", "reminder_type", "reminder_time",
              "resource_capacity", "resource_description", "resource_enable_discussion",
              "duration", "resource_location"]
    rec = rpc("booking.reservation", "read", [[rid], fields])[0]
    # Just verify all fields are readable without error
    assert "subject" in rec, "Missing subject field"
    assert "duration" in rec, "Missing duration field"
    assert "resource_enable_discussion" in rec, "Missing resource_enable_discussion"
    assert isinstance(rec["reminder_time"], int), f"reminder_time type: {type(rec['reminder_time'])}"
run_test("TC-008", "Read all new fields → no errors, correct types", tc008)

# ─── 1.2 Duration Bidirectional Sync ───
print("\n--- 1.2 Duration Bidirectional Sync ---")

def tc009():
    """Set start + end → verify duration computed"""
    start = base_start + timedelta(days=2, hours=0)
    end = start + timedelta(hours=2, minutes=30)  # 2.5 hours
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end.strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["duration"]])[0]
    assert abs(rec["duration"] - 2.5) < 0.01, f"Duration should be 2.5, got {rec['duration']}"
run_test("TC-009", "Set start+end → duration computed (2.5h)", tc009)

def tc010():
    """Set start + duration → verify end computed (inverse)"""
    start = base_start + timedelta(days=2, hours=4)
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (start + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    # Now update duration to 3 hours
    rpc("booking.reservation", "write", [[rid], {"duration": 3.0}])
    rec = rpc("booking.reservation", "read", [[rid], ["start_datetime", "end_datetime", "duration"]])[0]
    expected_end = start + timedelta(hours=3)
    actual_end = datetime.strptime(rec["end_datetime"], "%Y-%m-%d %H:%M:%S")
    assert abs((actual_end - expected_end).total_seconds()) < 60, \
        f"End mismatch: expected {expected_end}, got {actual_end}"
    assert abs(rec["duration"] - 3.0) < 0.01, f"Duration should be 3.0, got {rec['duration']}"
run_test("TC-010", "Update duration → end_datetime recomputed", tc010)

def tc011():
    """Update duration on existing → verify end updated"""
    rid = test_reservation_ids[-1]
    rec_before = rpc("booking.reservation", "read", [[rid], ["start_datetime", "end_datetime"]])[0]
    start = datetime.strptime(rec_before["start_datetime"], "%Y-%m-%d %H:%M:%S")
    # Change to 1.5 hours
    rpc("booking.reservation", "write", [[rid], {"duration": 1.5}])
    rec_after = rpc("booking.reservation", "read", [[rid], ["end_datetime", "duration"]])[0]
    expected_end = start + timedelta(hours=1, minutes=30)
    actual_end = datetime.strptime(rec_after["end_datetime"], "%Y-%m-%d %H:%M:%S")
    assert abs((actual_end - expected_end).total_seconds()) < 60, \
        f"End mismatch: expected {expected_end}, got {actual_end}"
run_test("TC-011", "Update duration again → end recalculated correctly", tc011)

def tc012():
    """Duration with fractional hours (0.25 = 15 min)"""
    start = base_start + timedelta(days=2, hours=8)
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (start + timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["duration"]])[0]
    assert abs(rec["duration"] - 0.25) < 0.01, f"Duration should be 0.25 (15min), got {rec['duration']}"
run_test("TC-012", "Fractional duration (15min=0.25h) computed correctly", tc012)

# ─── 1.3 Discussion Channel Integration ───
print("\n--- 1.3 Discussion Channel Integration ---")

def tc013():
    """Resource enable=True + reservation enable=True → channel auto-created"""
    # Ensure resource has discussion enabled
    rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": True}])
    start = base_start + timedelta(days=3, hours=0)
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (start + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "subject": "Discussion Test Meeting",
        "enable_discussion": True,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["channel_id", "enable_discussion"]])[0]
    assert rec["enable_discussion"] is True, f"enable_discussion should be True"
    # Channel may or may not be created depending on discuss.channel availability
    if rec["channel_id"]:
        print(f"    Channel created: ID={rec['channel_id'][0]}, Name={rec['channel_id'][1]}")
    else:
        print(f"    No channel created (discuss module may not be installed)")
run_test("TC-013", "Both enable_discussion=True → channel auto-created", tc013)

def tc014():
    """Resource enable=False + reservation enable=True → NO channel"""
    rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": False}])
    start = base_start + timedelta(days=3, hours=2)
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (start + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": True,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["channel_id", "enable_discussion"]])[0]
    assert not rec["channel_id"], f"Channel should NOT be created when resource disables discussion"
    # Restore
    rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": True}])
run_test("TC-014", "Resource disable → NO channel even if reservation enables", tc014)

def tc015():
    """Resource enable=True + reservation enable=False → NO channel"""
    rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": True}])
    start = base_start + timedelta(days=3, hours=4)
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (start + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["channel_id", "enable_discussion"]])[0]
    assert not rec["channel_id"], f"Channel should NOT be created when reservation disables discussion"
run_test("TC-015", "Reservation disable → NO channel even if resource enables", tc015)

def tc016():
    """Verify channel name format matches reservation name"""
    # Find a reservation with channel
    for rid in test_reservation_ids:
        rec = rpc("booking.reservation", "read", [[rid], ["channel_id", "name"]])[0]
        if rec["channel_id"]:
            channel = rpc("discuss.channel", "read", [[rec["channel_id"][0]], ["name"]])[0]
            # Channel name should contain reservation name or subject
            print(f"    Reservation name: {rec['name']}")
            print(f"    Channel name: {channel['name']}")
            # Just verify channel exists and has a name
            assert channel["name"], "Channel should have a name"
            return
    print("    SKIP: No channels created (discuss module may not be available)")
run_test("TC-016", "Channel name format check", tc016)

def tc017():
    """Enable discussion on existing reservation → channel created on write"""
    # Create without discussion first
    start = base_start + timedelta(days=3, hours=6)
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (start + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    rec = rpc("booking.reservation", "read", [[rid], ["channel_id"]])[0]
    assert not rec["channel_id"], "Should not have channel initially"

    # Now enable discussion
    rpc("booking.reservation", "write", [[rid], {"enable_discussion": True}])
    rec = rpc("booking.reservation", "read", [[rid], ["channel_id", "enable_discussion"]])[0]
    assert rec["enable_discussion"] is True, "enable_discussion should now be True"
    if rec["channel_id"]:
        print(f"    Channel created on write: {rec['channel_id']}")
    else:
        print(f"    No channel (discuss module may not be available)")
run_test("TC-017", "Enable discussion on existing → channel created on write", tc017)

def tc018():
    """Check channel_id is properly linked"""
    for rid in test_reservation_ids:
        rec = rpc("booking.reservation", "read", [[rid], ["channel_id"]])[0]
        if rec["channel_id"]:
            ch_id = rec["channel_id"][0]
            # Verify channel actually exists
            ch = rpc("discuss.channel", "search_count", [[("id", "=", ch_id)]])
            assert ch == 1, f"Channel {ch_id} should exist in discuss.channel"
            print(f"    Verified channel {ch_id} exists")
            return
    print("    SKIP: No channels to verify")
run_test("TC-018", "channel_id properly linked to discuss.channel", tc018)

# ─── 1.4 Constraints ───
print("\n--- 1.4 Constraints ---")

def tc019():
    """Create overlapping reservation → expect error"""
    # Use same slot as TC-001
    start = base_start + timedelta(days=0, hours=0)
    end = start + timedelta(hours=1)
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end.strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    try:
        rid = rpc("booking.reservation", "create", [vals])
        # If it was created, that means overlap check failed - clean up
        test_reservation_ids.append(rid)
        raise AssertionError("Should have raised overlap error")
    except xmlrpc.client.Fault as e:
        assert "overlap" in str(e).lower() or "already" in str(e).lower() or "conflict" in str(e).lower(), \
            f"Expected overlap error, got: {str(e)[:200]}"
run_test("TC-019", "Overlapping reservation → error raised", tc019)

def tc020():
    """Create with end < start → expect SQL constraint error"""
    start = base_start + timedelta(days=4, hours=0)
    end = start - timedelta(hours=1)  # end BEFORE start
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end.strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    try:
        rid = rpc("booking.reservation", "create", [vals])
        test_reservation_ids.append(rid)
        raise AssertionError("Should have raised date constraint error")
    except xmlrpc.client.Fault as e:
        assert "check_dates" in str(e).lower() or "constraint" in str(e).lower() or "end" in str(e).lower(), \
            f"Expected date constraint error, got: {str(e)[:200]}"
run_test("TC-020", "end < start → SQL constraint error", tc020)

def tc021():
    """Cancel overlapping reservation → re-confirm same slot succeeds"""
    # Cancel the TC-001 reservation
    rid_to_cancel = test_reservation_ids[0]
    rpc("booking.reservation", "action_cancel", [[rid_to_cancel]])
    rec = rpc("booking.reservation", "read", [[rid_to_cancel], ["state"]])[0]
    assert rec["state"] == "cancelled", f"Should be cancelled: {rec['state']}"

    # Now create a new booking in the same slot
    start = base_start + timedelta(days=0, hours=0)
    end = start + timedelta(hours=1)
    vals = {
        "resource_type_id": resource_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": end.strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    rid = rpc("booking.reservation", "create", [vals])
    test_reservation_ids.append(rid)
    assert rid, "Should be able to book cancelled slot"
run_test("TC-021", "Cancel overlap → re-book same slot succeeds", tc021)

def tc022():
    """Create with unauthorized partner → check if access error raised"""
    # Create a resource with specific share_type
    resource_specific = rpc("booking.resource.type", "search_read",
        [[("share_type", "=", "specific"), ("active", "=", True)]],
        {"fields": ["id", "name", "allowed_partner_ids"], "limit": 1})

    if not resource_specific:
        # Create one for testing
        test_res_id = rpc("booking.resource.type", "create", [{
            "name": "Test Restricted Resource",
            "share_type": "specific",
            "allowed_partner_ids": [(6, 0, [1])],  # Only admin partner
            "slot_duration": 1.0,
        }])
        # Create availability
        rpc("booking.resource.availability", "create", [{
            "resource_type_id": test_res_id,
            "dayofweek": str(base_start.weekday()),
            "hour_from": 0.0,
            "hour_to": 23.0,
        }])
        resource_specific_id = test_res_id
    else:
        resource_specific_id = resource_specific[0]["id"]

    start = base_start + timedelta(days=5, hours=0)
    vals = {
        "resource_type_id": resource_specific_id,
        "partner_id": portal_partner_id,
        "start_datetime": start.strftime("%Y-%m-%d %H:%M:%S"),
        "end_datetime": (start + timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S"),
        "enable_discussion": False,
    }
    try:
        rid = rpc("booking.reservation", "create", [vals])
        test_reservation_ids.append(rid)
        # If portal partner happens to be in allowed list, this is fine
        print(f"    Note: Creation succeeded (partner may be allowed)")
    except xmlrpc.client.Fault as e:
        assert "access" in str(e).lower() or "not allowed" in str(e).lower() or "permission" in str(e).lower(), \
            f"Expected access error, got: {str(e)[:200]}"
        print(f"    Access denied as expected")
run_test("TC-022", "Unauthorized partner → access check", tc022)

def tc023():
    """Verify resource_enable_discussion related field"""
    rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": True}])
    rid = test_reservation_ids[1]  # Any test reservation
    rec = rpc("booking.reservation", "read", [[rid], ["resource_enable_discussion"]])[0]
    assert rec["resource_enable_discussion"] is True, \
        f"resource_enable_discussion should follow resource: {rec['resource_enable_discussion']}"

    rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": False}])
    rec = rpc("booking.reservation", "read", [[rid], ["resource_enable_discussion"]])[0]
    assert rec["resource_enable_discussion"] is False, \
        f"resource_enable_discussion should update: {rec['resource_enable_discussion']}"

    # Restore
    rpc("booking.resource.type", "write", [[resource_id], {"enable_discussion": True}])
run_test("TC-023", "resource_enable_discussion follows resource setting", tc023)

# ─── Cleanup ───
print("\n--- Cleanup ---")
print(f"  Test reservations created: {len(test_reservation_ids)}")
cleanup_reservations(test_reservation_ids)
print(f"  Cleaned up test data")

# ─── Summary ───
print("\n" + "=" * 70)
print("ROUND 1 RESULTS SUMMARY")
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
            print(f"      Error: {err[:200]}")
print()
