/** @odoo-module **/

import { registry } from "@web/core/registry";
import { calendarView } from "@web/views/calendar/calendar_view";
import { BookingCalendarController } from "./booking_calendar_controller";

export const bookingCalendarView = {
    ...calendarView,
    Controller: BookingCalendarController,
};

registry.category("views").add("odoo_booking_reservation.booking_calendar", bookingCalendarView);
