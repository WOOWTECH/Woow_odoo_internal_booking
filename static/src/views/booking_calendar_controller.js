/** @odoo-module **/

import { CalendarController } from "@web/views/calendar/calendar_controller";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class BookingCalendarController extends CalendarController {
    setup() {
        super.setup();
        this.actionService = useService("action");
        this.newButtonLabel = _t("New");
    }

    onClickAddButton() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "booking.reservation",
            name: _t("New Reservation"),
            view_mode: "form",
            views: [[false, "form"]],
            target: "current",
            res_id: false,
        });
    }
}

BookingCalendarController.template = "booking_reservation.BookingCalendarController";
