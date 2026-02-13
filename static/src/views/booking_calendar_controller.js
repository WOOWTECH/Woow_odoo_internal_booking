/** @odoo-module **/

import { CalendarController } from "@web/views/calendar/calendar_controller";
import { useService } from "@web/core/utils/hooks";

export class BookingCalendarController extends CalendarController {
    setup() {
        super.setup();
        this.actionService = useService("action");
    }

    onClickAddButton() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "booking.reservation",
            name: "New Reservation",
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            res_id: false,
        });
    }
}

BookingCalendarController.template = "booking_reservation.BookingCalendarController";
