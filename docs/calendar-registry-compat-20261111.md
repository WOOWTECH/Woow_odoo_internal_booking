# Calendar registry compatibility verification — 2026-11-11

Base: remote `origin/main`, `c4ddced` (fetched 2026-11-11).
Module: `odoo_booking_reservation`, version `18.0.1.0.4`.

## Change and layout

This repository root is the module directory. Sync its contents into an addons
folder named `odoo_booking_reservation`; do not nest the repository inside that
module folder. The manifest is at the repository root.

The JS registration and `view_booking_reservation_calendar` XML `js_class` now
both use `odoo_booking_reservation.booking_calendar`. The three calendars in
`reservation_module` retain `booking_calendar`. Controller implementations,
OWL template names, dependencies and asset inclusion are unchanged.

## Local regression evidence

Executed a Node VM harness against the actual controller/view JS sources, with
Odoo framework services and a duplicate-rejecting registry stub. Compared the
base JS (`git show HEAD:static/src/views/booking_calendar_view.js`) against the
patched working tree. The other module was read from:
the `Odoo_reservation_module` repository, module-relative directory `reservation_module/`.

Results in both module load orders:

- Base: duplicate `booking_calendar` reproduced as expected.
- Patch: both keys register successfully and resolve to distinct controllers.
- Resource calendar New action targets `booking.reservation`.
- Appointment calendar New invokes `editRecord({}, {}, false)`.
- Each controller retains its own OWL template name.

Python XML parsing confirmed one namespaced resource calendar and three legacy
appointment calendars. Manifest parsing confirmed version `18.0.1.0.4` and
inclusion of the updated view XML. `git diff --check` passed.

These checks are local isolated checks, not Odoo/browser integration results.
No database or deployed service was changed.

## Isolated database verification pending

The coordinating agent must sync this module and upgrade
`odoo_booking_reservation` in the isolated database, refreshing backend assets
with the updated stored view architecture. Verify backend startup without the
duplicate registry exception, then resource and appointment calendars and their
New actions (including the appointment resource/staff variants). Existing custom
views explicitly using the old key for resource bookings must also be checked
before any broader deployment.

## Bounded browser attempt — 2026-11-11

Used Python Playwright Chromium and the supplied clone manager on port 18109
(after the coordinating agent reported the 18.0.1.0.4 upgrade).
Login reached the backend Discuss screen. For both `booking.reservation` and
`appointment.booking`, authenticated `check_access_rights` calls returned false
for both read and create. Direct calendar navigation did not display a calendar
within the bounded 18-second wait per model; screenshots retained the Discuss
screen. No New form was reached, and no reservation was saved.

No uncaught browser JavaScript errors were captured during this attempt. This
alone does not establish calendar/controller correctness. The coordinating agent
reported concurrent connection-pool pressure, but this attempt's recorded errors
were calendar locator timeouts, not a confirmed ConnectionPoolFull exception.

Private evidence is stored outside this repository in sibling directory
`booking-browser-private-20261111/`: `verify_calendars.py`, `result.json`, and
`booking.reservation-failure.png` / `appointment.booking-failure.png`.
Credentials were read in memory; no credentials were copied into this document.
The browser and verification process exited before the coordinating agent's
final test run. No server or account configuration was changed.

Still unverified: actual calendar rendering for either model; live registry and
active controller selection; both New actions; appointment resource/staff
variants; save/edit flows and custom inherited views. Calendar acceptance needs
an authorized clone account with the required booking permissions; no permission
changes were made in this task.
