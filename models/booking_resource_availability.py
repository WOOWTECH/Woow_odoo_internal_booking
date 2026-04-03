from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _


class BookingResourceAvailability(models.Model):
    _name = 'booking.resource.availability'
    _description = '資源可用時段'
    _order = 'dayofweek, hour_from'

    resource_type_id = fields.Many2one(
        'booking.resource.type',
        string='資源',
        required=True,
        ondelete='cascade',
    )

    dayofweek = fields.Selection(
        selection=[
            ('0', '星期一'),
            ('1', '星期二'),
            ('2', '星期三'),
            ('3', '星期四'),
            ('4', '星期五'),
            ('5', '星期六'),
            ('6', '星期日'),
        ],
        string='星期',
        required=True,
        default='0',
    )

    hour_from = fields.Float(
        string='開始時間',
        required=True,
        default=9.0,
        help='24 小時制開始時間（例如 9.0 代表 09:00，14.5 代表 14:30）',
    )

    hour_to = fields.Float(
        string='結束時間',
        required=True,
        default=18.0,
        help='24 小時制結束時間（例如 18.0 代表 18:00，17.5 代表 17:30）',
    )

    @api.constrains('hour_from', 'hour_to')
    def _check_hours(self):
        for record in self:
            if record.hour_from < 0 or record.hour_from > 24:
                raise ValidationError(_('開始時間必須在 0 到 24 之間。'))
            if record.hour_to < 0 or record.hour_to > 24:
                raise ValidationError(_('結束時間必須在 0 到 24 之間。'))
            if record.hour_from >= record.hour_to:
                raise ValidationError(_('開始時間必須在結束時間之前。'))

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
