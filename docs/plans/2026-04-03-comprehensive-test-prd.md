# PRD: Comprehensive Enterprise-Grade Testing — odoo_booking_reservation

**Module:** odoo_booking_reservation v18.0.1.0.0
**Date:** 2026-04-03
**Environment:** Podman container `odoo-calendar-web` on port 9071
**Database:** odoocalendar
**Target:** 商用企業部署應用等級 (Enterprise deployment-grade)

---

## 1. Test Scope

### 1.1 Features Under Test

| Feature | New? | Priority |
|---------|------|----------|
| Subject field + name computation | NEW | P0 |
| Description (Html) field | NEW | P0 |
| Organizer / Attendees | NEW | P0 |
| Discussion channel integration | NEW | P0 |
| Duration bidirectional sync | NEW | P0 |
| Reminder fields | NEW | P1 |
| Resource enable_discussion toggle | NEW | P0 |
| Portal confirm page (redesigned) | MODIFIED | P0 |
| Portal detail page (redesigned) | MODIFIED | P0 |
| Backend reservation form (redesigned) | MODIFIED | P0 |
| Resource type Advanced Settings tab | NEW | P1 |
| zh_TW translations | NEW | P1 |
| Existing: slot generation | EXISTING | P0 |
| Existing: overlap prevention | EXISTING | P0 |
| Existing: access control | EXISTING | P0 |
| Existing: CRUD operations | EXISTING | P0 |

### 1.2 Test Layers

```
┌─────────────────────────────────────────┐
│  Layer 1: Browser UI (Chrome DevTools)  │  ← User-facing
├─────────────────────────────────────────┤
│  Layer 2: HTTP Controller (curl)        │  ← Route logic
├─────────────────────────────────────────┤
│  Layer 3: XML-RPC API                   │  ← Business logic
├─────────────────────────────────────────┤
│  Layer 4: Database / Data Integrity     │  ← Data layer
└─────────────────────────────────────────┘
```

---

## 2. Test Plan

### Round 1: API/RPC Layer (30+ test cases)

**1.1 New Field CRUD**
- TC-001: Create reservation with subject → verify name uses subject
- TC-002: Create reservation without subject → verify name uses resource+datetime
- TC-003: Create reservation with description (HTML content)
- TC-004: Create reservation with organizer_id
- TC-005: Create reservation with attendee_ids (multiple partners)
- TC-006: Update subject → verify name recomputed
- TC-007: Set reminder_type and reminder_time
- TC-008: Read all new fields back and verify types/values

**1.2 Duration Bidirectional Sync**
- TC-009: Set start + end → verify duration computed
- TC-010: Set start + duration → verify end computed (inverse)
- TC-011: Update duration on existing → verify end updated
- TC-012: Duration with fractional hours (1.5, 0.25)

**1.3 Discussion Channel Integration**
- TC-013: Resource enable_discussion=True + reservation enable_discussion=True → channel auto-created
- TC-014: Resource enable_discussion=False + reservation enable_discussion=True → NO channel
- TC-015: Resource enable_discussion=True + reservation enable_discussion=False → NO channel
- TC-016: Verify channel name format matches reservation name
- TC-017: Enable discussion on existing reservation → channel created on write
- TC-018: Check channel_id is properly linked

**1.4 Constraints**
- TC-019: Create overlapping reservation → expect error
- TC-020: Create with end < start → expect SQL constraint error
- TC-021: Cancel overlapping reservation → re-confirm same slot succeeds
- TC-022: Create with unauthorized partner → expect access error
- TC-023: Verify resource_enable_discussion related field

### Round 2: HTTP/Controller Layer (20+ test cases)

**2.1 Portal Routes**
- TC-024: GET /my/bookings → 200, shows booking list
- TC-025: GET /my/booking/resources → 200, shows resource cards
- TC-026: GET /my/booking/resources/{id} → 200, shows slots
- TC-027: GET /my/bookings/confirm?resource_id=&start=&end= → 200, shows form
- TC-028: POST /my/bookings/create → 302 redirect, booking created
- TC-029: GET /my/bookings/{id} → 200, shows booking detail
- TC-030: POST /my/bookings/{id}/cancel → redirect, booking cancelled

**2.2 New Form Fields**
- TC-031: Submit with subject → stored in reservation
- TC-032: Submit with description → stored as HTML
- TC-033: Submit with enable_discussion=on → channel created (if resource allows)
- TC-034: Submit without subject → reservation has auto-generated name
- TC-035: Organizer auto-set to current portal user's partner

**2.3 Error Handling**
- TC-036: Confirm page with invalid resource_id → 404 or error
- TC-037: Confirm page with past datetime → error handling
- TC-038: Create with missing required fields → error
- TC-039: Cancel already-cancelled booking → graceful handling
- TC-040: Access other user's booking → 403

### Round 3: Browser/UI (Chrome DevTools) (15+ test cases)

**3.1 Backend Admin Form**
- TC-041: Open reservation form → subject field visible as h1
- TC-042: Select resource → resource info panel appears
- TC-043: Fill subject → name updates in real-time
- TC-044: Duration field shows float_time widget
- TC-045: Discussion section visible when resource allows it
- TC-046: Resource type form → Advanced Settings tab visible

**3.2 Portal Pages**
- TC-047: Resource list shows cards with Book Now buttons
- TC-048: Resource detail shows slot grid
- TC-049: Click slot → redirects to confirm page
- TC-050: Confirm page shows subject input, discussion checkbox
- TC-051: Booking detail shows all new sections
- TC-052: My Bookings list shows correct data

### Round 4: Edge Cases (10+ test cases)

- TC-053: Unicode subject (中文、日本語、emoji)
- TC-054: Very long subject (>255 chars)
- TC-055: HTML injection in description field
- TC-056: XSS attempt in subject field
- TC-057: Concurrent booking same slot (race condition)
- TC-058: Booking at midnight boundary
- TC-059: Booking across DST transition
- TC-060: Resource with 0 capacity
- TC-061: Empty attendee_ids
- TC-062: Duration = 0

### Round 5: Security (10+ test cases)

- TC-063: Portal user can only see own bookings via API
- TC-064: Portal user cannot read other user's channel_id
- TC-065: CSRF token required for create/cancel
- TC-066: Non-authenticated access → redirect to login
- TC-067: Portal user cannot modify resource enable_discussion
- TC-068: SQL injection attempt in search
- TC-069: Path traversal in booking_id parameter
- TC-070: Admin can see all bookings

### Round 6: Data Integrity (5+ test cases)

- TC-071: Delete resource → reservations restricted (no cascade)
- TC-072: Cancel reservation → discussion channel preserved
- TC-073: Bulk create → no data corruption
- TC-074: Verify related fields sync when resource updated
- TC-075: Timezone consistency across API and portal

---

## 3. Success Criteria

- **Zero P0 failures** — All critical features work correctly
- **Zero security vulnerabilities** — Access control, CSRF, injection all pass
- **Zero data corruption** — Constraints enforced, related fields sync
- **All portal pages render** — 200 status, correct content
- **Backend forms functional** — All new fields visible and editable
- **Discussion integration works** — Channel auto-creation when enabled
- **Duration sync works** — Bidirectional computation correct

---

## 4. Test Environment

| Parameter | Value |
|-----------|-------|
| Odoo Version | 18.0 |
| Container | odoo-calendar-web |
| Host Port | 9071 |
| Database | odoocalendar |
| Admin | admin / admin |
| Portal User | portal / portal |
| Network | odoo-calendar-network |

---

## 5. Deliverables

1. This PRD document
2. Executed test results with pass/fail for each TC
3. Any bugs found documented with reproduction steps
4. Fix commits for any issues discovered
5. Final enterprise-readiness assessment
