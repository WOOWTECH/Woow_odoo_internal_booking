from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class BookingResourceAvailability(models.Model):
    _name = 'booking.resource.availability'
    _description = 'Resource Availability'
    _order = 'dayofweek, hour_from'

    resource_type_id = fields.Many2one(
        'booking.resource.type',
        string='Resource',
        required=True,
        ondelete='cascade',
    )

    dayofweek = fields.Selection(
        selection=[
            ('0', 'Monday'),
            ('1', 'Tuesday'),
            ('2', 'Wednesday'),
            ('3', 'Thursday'),
            ('4', 'Friday'),
            ('5', 'Saturday'),
            ('6', 'Sunday'),
        ],
        string='Day of Week',
        required=True,
        default='0',
    )

    hour_from = fields.Float(
        string='Start Time',
        required=True,
        default=9.0,
        help='Start time in 24-hour format (e.g. 9.0 = 09:00, 14.5 = 14:30)',
    )

    hour_to = fields.Float(
        string='End Time',
        required=True,
        default=18.0,
        help='End time in 24-hour format (e.g. 18.0 = 18:00, 17.5 = 17:30)',
    )

    @api.constrains('hour_from', 'hour_to')
    def _check_hours(self):
        for record in self:
            if record.hour_from < 0 or record.hour_from > 24:
                raise ValidationError(_('Start time must be between 0 and 24.'))
            if record.hour_to < 0 or record.hour_to > 24:
                raise ValidationError(_('End time must be between 0 and 24.'))
            if record.hour_from >= record.hour_to:
                raise ValidationError(_('Start time must be before end time.'))

    @api.constrains('resource_type_id', 'dayofweek', 'hour_from', 'hour_to')
    def _check_no_overlap(self):
        """Prevent overlapping availability windows for the same resource on the same day."""
        for record in self:
            overlapping = self.search([
                ('id', '!=', record.id),
                ('resource_type_id', '=', record.resource_type_id.id),
                ('dayofweek', '=', record.dayofweek),
                ('hour_from', '<', record.hour_to),
                ('hour_to', '>', record.hour_from),
            ], limit=1)
            if overlapping:
                raise ValidationError(
                    _('Availability overlap: %s %s-%s conflicts with %s-%s.') % (
                        dict(self._fields['dayofweek'].selection).get(record.dayofweek),
                        record._format_hour(record.hour_from),
                        record._format_hour(record.hour_to),
                        overlapping._format_hour(overlapping.hour_from),
                        overlapping._format_hour(overlapping.hour_to),
                    )
                )

    def _format_hour(self, hour):
        """Convert float hour to HH:MM format."""
        hours = int(hour)
        minutes = int((hour % 1) * 60)
        return f'{hours:02d}:{minutes:02d}'

    def name_get(self):
        days = dict(self._fields['dayofweek'].selection)
        result = []
        for record in self:
            day_name = days.get(record.dayofweek, '')
            time_from = record._format_hour(record.hour_from)
            time_to = record._format_hour(record.hour_to)
            result.append((record.id, f'{day_name} {time_from} - {time_to}'))
        return result
