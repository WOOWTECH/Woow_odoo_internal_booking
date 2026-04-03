from odoo import api, fields, models
from odoo.exceptions import ValidationError
from odoo.tools.translate import _
from datetime import datetime, timedelta


class BookingResourceType(models.Model):
    _name = 'booking.resource.type'
    _description = '預定資源'
    _inherit = ['mail.thread']
    _order = 'sequence, name'

    # 基本資訊
    name = fields.Char(
        string='名稱',
        required=True,
        translate=True,
        tracking=True,
    )
    description = fields.Html(
        string='說明',
        translate=True,
    )
    image = fields.Image(
        string='圖片',
        max_width=512,
        max_height=512,
    )
    sequence = fields.Integer(
        string='排序',
        default=10,
    )
    active = fields.Boolean(
        string='啟用',
        default=True,
        tracking=True,
    )

    # 資源詳情
    location = fields.Char(
        string='地點',
        translate=True,
    )
    capacity = fields.Integer(
        string='容量',
        default=1,
        help='資源的最大容量',
    )

    # 時段設定
    slot_duration = fields.Float(
        string='時段長度（小時）',
        default=1.0,
        required=True,
        help='每個預定時段的時長（小時）',
    )
    slot_interval = fields.Float(
        string='時段間隔（小時）',
        default=1.0,
        help='可用時段之間的間隔時間。設定與時段長度相同可避免時段重疊。',
    )
    advance_days = fields.Integer(
        string='可預定天數',
        default=30,
        help='使用者可提前多少天預定此資源',
    )

    # 可用時段（每週重複排程）
    availability_ids = fields.One2many(
        'booking.resource.availability',
        'resource_type_id',
        string='可用時段',
        help='定義每週各天的重複可用時段',
    )

    # 討論設定
    enable_discussion = fields.Boolean(
        string='允許討論通道',
        default=False,
        help='啟用後，預定此資源的使用者可選擇為該預定建立討論通道。',
    )

    # 存取控制
    share_type = fields.Selection(
        selection=[
            ('all', '所有 Portal 使用者'),
            ('specific', '特定聯絡人'),
        ],
        string='存取類型',
        default='specific',
        required=True,
        tracking=True,
        help='控制誰可以預定此資源',
    )
    allowed_partner_ids = fields.Many2many(
        'res.partner',
        'booking_resource_type_partner_rel',
        'resource_type_id',
        'partner_id',
        string='允許的聯絡人',
        domain="[('is_company', '=', False)]",
        help='選擇可預定此資源的聯絡人（Portal 使用者）。僅在存取類型為「特定聯絡人」時適用。',
    )

    # 分類（用於屬性定義）
    category_id = fields.Many2one(
        'booking.resource.category',
        string='分類',
        ondelete='set null',
        index=True,
    )

    # 動態屬性（Odoo 18 原生功能）
    resource_properties = fields.Properties(
        string='屬性',
        definition='category_id.resource_properties_definition',
        copy=True,
    )

    # 關聯預定
    reservation_ids = fields.One2many(
        'booking.reservation',
        'resource_type_id',
        string='預定',
    )
    reservation_count = fields.Integer(
        string='預定數量',
        compute='_compute_reservation_count',
    )

    @api.depends('reservation_ids')
    def _compute_reservation_count(self):
        for record in self:
            record.reservation_count = len(record.reservation_ids.filtered(
                lambda r: r.state == 'confirmed'
            ))

    @api.constrains('slot_duration', 'slot_interval')
    def _check_slot_settings(self):
        for record in self:
            if record.slot_duration <= 0:
                raise ValidationError(_('時段長度必須為正數。'))
            if record.slot_interval <= 0:
                raise ValidationError(_('時段間隔必須為正數。'))

    @api.constrains('advance_days')
    def _check_advance_days(self):
        for record in self:
            if record.advance_days < 1:
                raise ValidationError(_('可預定天數至少為 1 天。'))

    def _check_partner_access(self, partner):
        """Check if a partner has access to book this resource."""
        self.ensure_one()
        if self.share_type == 'all':
            return True
        return partner.id in self.allowed_partner_ids.ids

    def _generate_slots(self, date_from, date_to):
        """
        Generate available time slots for this resource.

        Args:
            date_from: Start date
            date_to: End date

        Returns:
            List of slot dictionaries with start/end datetime and availability
        """
        self.ensure_one()
        slots = []
        current_date = date_from

        while current_date <= date_to:
            day_of_week = str(current_date.weekday())
            availabilities = self.availability_ids.filtered(
                lambda a: a.dayofweek == day_of_week
            )

            for availability in availabilities:
                current_hour = availability.hour_from

                while current_hour + self.slot_duration <= availability.hour_to:
                    # Create datetime for slot start
                    hour = int(current_hour)
                    minute = int((current_hour % 1) * 60)
                    start_dt = datetime.combine(
                        current_date,
                        datetime.min.time().replace(hour=hour, minute=minute)
                    )
                    end_dt = start_dt + timedelta(hours=self.slot_duration)

                    slots.append({
                        'start': start_dt,
                        'end': end_dt,
                        'start_str': start_dt.strftime('%Y-%m-%d %H:%M'),
                        'end_str': end_dt.strftime('%H:%M'),
                        'date_str': start_dt.strftime('%Y-%m-%d'),
                    })

                    current_hour += self.slot_interval

            current_date += timedelta(days=1)

        return slots

    def action_view_reservations(self):
        """Open reservations for this resource."""
        self.ensure_one()
        return {
            'name': _('預定'),
            'type': 'ir.actions.act_window',
            'res_model': 'booking.reservation',
            'view_mode': 'calendar,tree,form',
            'domain': [('resource_type_id', '=', self.id)],
            'context': {'default_resource_type_id': self.id},
        }
