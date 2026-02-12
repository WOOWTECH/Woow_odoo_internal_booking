# Odoo 18 資源預約模組 PRD

**文件版本**: 1.2
**日期**: 2026-02-12
**狀態**: Draft
**模組名稱**: `booking_reservation`

---

## 1. 執行摘要

### 問題陳述
Odoo 18 Community 版本的日曆功能缺乏完整的資源預約管理能力，無法讓 Portal 用戶自主預約會議室或其他共享資源，企業需要額外的解決方案來管理內部資源預約需求。

### 提案解決方案
開發一個獨立的資源預約模組，擴展 Odoo 18 日曆功能，支援 Portal 用戶透過 Portal 介面預約資源。管理員可在資源預約類型設定中指定哪些聯絡人（Portal 用戶）有權預約該資源，且不依賴網站 (website) 模組。

### 業務影響
- 提升內部資源使用效率，減少預約衝突
- 透過聯絡人分享機制，精確控制誰可以預約哪些資源
- 降低 IT 維護成本，模組與網站模組解耦

### 成功指標
| 指標 | 目標 |
|------|------|
| Portal 用戶預約成功率 | > 95% |
| 預約衝突率 | < 2% |
| 用戶操作完成時間 | < 30 秒 |

---

## 2. 問題定義

### 2.1 客戶問題

| 面向 | 說明 |
|------|------|
| **Who** | 企業內部員工、Portal 用戶（已登入的聯絡人） |
| **What** | 無法透過 Portal 預約會議室/資源，缺乏權限控管機制 |
| **When** | 日常會議安排、跨部門協作時 |
| **Where** | Odoo Portal 介面、後台日曆模組 |
| **Why** | Odoo 18 Community 日曆功能未提供 Portal 資源預約能力 |
| **Impact** | 手動協調耗時、預約衝突頻繁、資源使用率低 |

### 2.2 業務案例
- **策略價值**: 強化 Odoo 生態系統的協作能力
- **效率提升**: 減少人工協調時間 50%+
- **獨立部署**: 不依賴 website 模組，適合僅使用後台的企業

---

## 3. 解決方案概覽

### 3.1 提案解決方案

基於 Odoo 18 的日曆 (calendar) 模組，開發獨立的資源預約模組，核心功能包括：

1. **資源預約類型管理** - 後台管理可預約的資源（會議室、設備等），整合資源分類與項目設定
2. **Portal 預約介面** - Portal 用戶可在 Portal 頁面建立/查看/取消預約
3. **聯絡人權限分享** - 在資源預約類型設定中指定哪些聯絡人可預約該資源
4. **預約衝突檢測** - 自動檢測並防止時間衝突
5. **動態屬性系統** - 支援 Odoo 原生「加入屬性」功能，自訂資源欄位
6. **後台日曆視圖** - 在日曆模組下新增資源預約頁面，含篩選器與新增按鈕

### 3.2 範圍內 (In Scope)

| 功能 | 優先級 | 說明 |
|------|--------|------|
| 資源預約類型管理 | P0 | 整合資源分類與項目設定（取代獨立的資源類型） |
| 週期性時段設定 | P0 | 在資源表單中設定可預約時間，系統自動生成時段 |
| 時段長度/間隔設定 | P0 | 可在資源設定中自訂 slot_duration 和 slot_interval |
| Portal 預約介面 | P0 | Portal 用戶預約頁面 |
| 聯絡人權限分享 | P0 | 在資源表單設定可預約的聯絡人（Portal 用戶） |
| 預約衝突檢測 | P0 | 防止重複預約 |
| 動態屬性支援 | P0 | 使用 Odoo 原生「加入屬性」功能 |
| 後台日曆視圖 | P0 | 日曆模組下新增資源預約頁面 |
| 後台新增預約 | P0 | 後台可直接新增預約（彈出表單） |
| 資源篩選器 | P0 | 後台日曆視圖可篩選顯示哪些資源的預約 |
| 電子郵件通知 | P1 | 預約確認/提醒通知 |
| 日曆整合 | P1 | 與 Odoo 日曆事件同步 |
| 多語系支援 | P2 | 繁體中文、簡體中文、英文 |

### 3.3 範圍外 (Out of Scope)

- 付費預約功能（需整合付款模組）
- 網站前台頁面（本模組不依賴 website 模組）
- 外部匿名分享連結（所有預約者必須登入為 Portal 用戶）
- 視訊會議整合
- 餐桌預訂等特定行業功能
- 員工行程預約功能
- 預約審核流程（直接確認，無需審核）
- 最小提前預約時間限制
- 取消時間限制

### 3.4 MVP 定義

**核心功能集**:
1. 資源預約類型的 CRUD（含動態屬性）
2. 週期性可預約時段設定（slot_duration、slot_interval 可自訂）
3. 聯絡人權限分享設定（指定哪些 Portal 用戶可預約）
4. 後台日曆視圖（含資源篩選器、新增按鈕）
5. Portal 用戶預約介面（列表、日曆視圖）
6. 基本預約衝突檢測

**成功標準**:
- 管理員可設定資源的可預約聯絡人
- 後台和 Portal 都可以建立預約
- 被授權的 Portal 用戶可完成完整預約流程
- 系統正確阻擋衝突預約

---

## 4. 用戶故事與需求

### 4.1 用戶故事

#### US-001: 資源管理員建立資源預約類型
```
作為 資源管理員
我想要 在後台建立和管理資源預約類型
以便 讓用戶可以預約這些資源

驗收條件:
- [ ] 可建立資源預約類型（如：A會議室、B會議室、投影機）
- [ ] 可設定資源的基本資訊（名稱、位置、容量、說明、圖片）
- [ ] 可設定資源的可預約時段（週期性）
- [ ] 可設定時段長度（slot_duration）和間隔（slot_interval）
- [ ] 可使用「加入屬性」新增自訂欄位
- [ ] 可啟用/停用資源
```

#### US-002: Portal 用戶預約資源
```
作為 Portal 用戶
我想要 在 Portal 頁面預約會議室或資源
以便 安排我的會議或活動

驗收條件:
- [ ] 可在 Portal 看到可預約資源列表
- [ ] 可選擇資源和時段進行預約
- [ ] 可查看我的預約記錄
- [ ] 可取消我的預約
- [ ] 預約成功後收到確認通知
```

#### US-003: 管理員設定資源的可預約聯絡人
```
作為 資源管理員
我想要 在資源預約類型表單中設定哪些聯絡人可以預約該資源
以便 控制資源的使用權限

驗收條件:
- [ ] 可在資源表單中選擇多個聯絡人（Portal 用戶）
- [ ] 可設定為「所有 Portal 用戶」或「指定聯絡人」
- [ ] 未被授權的聯絡人無法在 Portal 看到該資源
- [ ] 可隨時新增或移除授權聯絡人
```

#### US-004: Portal 用戶查看可預約資源與時段
```
作為 被授權的 Portal 用戶
我想要 在 Portal 頁面看到我被授權預約的資源及其可用時段
以便 選擇合適的資源進行預約

驗收條件:
- [ ] 只能看到我被授權預約的資源
- [ ] 可查看資源的詳細資訊（位置、容量、說明、自訂屬性等）
- [ ] 可查看資源的可用時段
- [ ] 已被預約的時段顯示為不可用（但不揭露預約人資訊）
- [ ] 可直接從列表進入預約流程
```

#### US-005: 系統防止預約衝突
```
作為 系統
我需要 自動檢測預約時間衝突
以便 確保資源不會被重複預約

驗收條件:
- [ ] 選擇時段時顯示已被預約的時間（不揭露預約人）
- [ ] 提交衝突預約時顯示錯誤訊息
- [ ] 並發預約時正確處理競爭條件
```

#### US-006: 後台管理員在日曆視圖管理預約
```
作為 後台管理員
我想要 在日曆模組中查看和管理所有資源預約
以便 掌握資源使用狀況

驗收條件:
- [ ] 在日曆模組下有「資源預約」選單項目
- [ ] 可以日曆視圖顯示所有預約
- [ ] 可透過篩選器選擇顯示哪些資源的預約
- [ ] 可點擊「新增」按鈕直接建立預約
- [ ] 點擊新增後跳出預約表單（選擇資源、時間、預約人）
```

### 4.2 功能需求

| ID | 需求 | 優先級 | 備註 |
|----|------|--------|------|
| FR-001 | 資源預約類型 CRUD | P0 | 後台管理，整合分類與項目 |
| FR-002 | 動態屬性支援 | P0 | 使用 Odoo 原生「加入屬性」功能 |
| FR-003 | 週期性時段設定 | P0 | 在資源表單中設定 |
| FR-004 | 時段長度/間隔設定 | P0 | slot_duration、slot_interval 可自訂 |
| FR-005 | 聯絡人權限分享 | P0 | 在資源表單設定可預約的聯絡人 |
| FR-006 | 後台日曆視圖 | P0 | 日曆模組下新增「資源預約」頁面 |
| FR-007 | 後台新增預約 | P0 | 點擊新增按鈕跳出表單 |
| FR-008 | 資源篩選器 | P0 | 後台日曆視圖可篩選資源 |
| FR-009 | Portal 資源列表頁 | P0 | 僅顯示被授權的資源 |
| FR-010 | Portal 預約表單 | P0 | 日期時間選擇器 |
| FR-011 | Portal 我的預約頁 | P0 | 列表與日曆視圖 |
| FR-012 | 預約衝突檢測 | P0 | 即時檢測 |
| FR-013 | 隱藏他人預約資訊 | P0 | Portal 用戶只能看到「已被預約」，不顯示預約人 |
| FR-014 | 郵件通知 | P1 | 確認/提醒/取消 |
| FR-015 | 日曆事件同步 | P1 | calendar.event |
| FR-016 | 報表統計 | P2 | 使用率統計 |

### 4.3 非功能需求

| 類型 | 需求 |
|------|------|
| **效能** | 預約列表載入 < 2 秒 |
| **並發** | 支援 100+ 同時預約操作 |
| **安全** | Portal 用戶只能操作自己的預約；只能看到被授權的資源 |
| **隱私** | Portal 用戶看不到其他人的預約內容，只知道時段已被佔用 |
| **認證** | 所有預約操作需登入為 Portal 用戶或後台用戶 |
| **相容性** | Odoo 18 Community Edition |
| **獨立性** | 不依賴 website 模組 |
| **多語系** | 支援 en_US, zh_TW, zh_CN |

---

## 5. 技術規格

### 5.1 模組相依性

```python
'depends': ['base', 'mail', 'calendar', 'portal'],
```

**說明**:
- `base`: Odoo 核心
- `mail`: 郵件通知功能
- `calendar`: 日曆整合與後台選單
- `portal`: Portal 用戶介面

**不依賴**: `website`（關鍵設計決策）

### 5.2 資料模型

#### booking.resource.type（資源預約類型）
```python
class BookingResourceType(models.Model):
    _name = 'booking.resource.type'
    _description = 'Booking Resource Type'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, translate=True)
    description = fields.Html(translate=True)
    image = fields.Image()
    capacity = fields.Integer(default=1)
    location = fields.Char()
    active = fields.Boolean(default=True)

    # 可預約時段設定（週期性）
    availability_ids = fields.One2many('booking.resource.availability', 'resource_type_id')

    # 時段設定
    slot_duration = fields.Float(
        string='Slot Duration (hours)',
        default=1.0,
        required=True,
        help='Duration of each booking slot in hours'
    )
    slot_interval = fields.Float(
        string='Slot Interval (hours)',
        default=1.0,
        help='Time interval between available slots. Set same as duration for non-overlapping slots.'
    )

    # 聯絡人權限分享（核心功能）
    share_type = fields.Selection([
        ('all', 'All Portal Users'),
        ('specific', 'Specific Contacts'),
    ], default='specific', required=True, string='Access Type')
    allowed_partner_ids = fields.Many2many(
        'res.partner',
        'booking_resource_type_partner_rel',
        'resource_type_id',
        'partner_id',
        string='Allowed Contacts',
        domain="[('is_company', '=', False)]",
        help='Select contacts (Portal users) who can book this resource'
    )

    # 預約設定
    advance_days = fields.Integer(default=30, string='Advance Booking Days')

    def _check_partner_access(self, partner):
        """檢查聯絡人是否有權預約此資源"""
        self.ensure_one()
        if self.share_type == 'all':
            return True
        return partner in self.allowed_partner_ids
```

**動態屬性支援**:
模型將啟用 Odoo 原生的「加入屬性」功能（透過 `ir.model.fields` 動態欄位機制），允許管理員自訂資源欄位。

#### booking.resource.availability（可預約時段 - 週期性）
```python
class BookingResourceAvailability(models.Model):
    _name = 'booking.resource.availability'
    _description = 'Resource Availability'

    resource_type_id = fields.Many2one(
        'booking.resource.type',
        required=True,
        ondelete='cascade'
    )
    dayofweek = fields.Selection([
        ('0', 'Monday'),
        ('1', 'Tuesday'),
        ('2', 'Wednesday'),
        ('3', 'Thursday'),
        ('4', 'Friday'),
        ('5', 'Saturday'),
        ('6', 'Sunday')
    ], required=True, default='0')
    hour_from = fields.Float(required=True, default=9.0)
    hour_to = fields.Float(required=True, default=18.0)

    @api.constrains('hour_from', 'hour_to')
    def _check_hours(self):
        for record in self:
            if record.hour_from >= record.hour_to:
                raise ValidationError(_('Start time must be before end time.'))
            if record.hour_from < 0 or record.hour_to > 24:
                raise ValidationError(_('Hours must be between 0 and 24.'))

    def name_get(self):
        days = dict(self._fields['dayofweek'].selection)
        return [(rec.id, f"{days.get(rec.dayofweek)} {rec.hour_from:.2f} - {rec.hour_to:.2f}") for rec in self]
```

#### booking.reservation（預約記錄）
```python
class BookingReservation(models.Model):
    _name = 'booking.reservation'
    _description = 'Resource Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(compute='_compute_name', store=True)
    resource_type_id = fields.Many2one(
        'booking.resource.type',
        required=True,
        string='Resource'
    )

    # 預約時間
    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime(required=True)
    duration = fields.Float(compute='_compute_duration', store=True)

    # 預約人（必須是 Portal 用戶或後台用戶關聯的聯絡人）
    partner_id = fields.Many2one('res.partner', required=True, string='Booked By')

    # 狀態（無審核流程，直接確認）
    state = fields.Selection([
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], default='confirmed', tracking=True)

    # 關聯
    calendar_event_id = fields.Many2one('calendar.event')

    # 備註
    note = fields.Text()

    _sql_constraints = [
        ('check_dates', 'CHECK(end_datetime > start_datetime)',
         'End time must be after start time'),
    ]

    @api.depends('resource_type_id', 'start_datetime')
    def _compute_name(self):
        for record in self:
            if record.resource_type_id and record.start_datetime:
                record.name = f"{record.resource_type_id.name} - {record.start_datetime}"
            else:
                record.name = "New Reservation"

    @api.depends('start_datetime', 'end_datetime')
    def _compute_duration(self):
        for record in self:
            if record.start_datetime and record.end_datetime:
                delta = record.end_datetime - record.start_datetime
                record.duration = delta.total_seconds() / 3600
            else:
                record.duration = 0

    @api.constrains('resource_type_id', 'partner_id')
    def _check_partner_access(self):
        """確保預約人有權預約該資源"""
        for record in self:
            if not record.resource_type_id._check_partner_access(record.partner_id):
                raise ValidationError(_('You are not authorized to book this resource.'))

    @api.constrains('resource_type_id', 'start_datetime', 'end_datetime')
    def _check_no_overlap(self):
        """檢查預約時間是否衝突"""
        for record in self:
            if record.state == 'cancelled':
                continue
            domain = [
                ('id', '!=', record.id),
                ('resource_type_id', '=', record.resource_type_id.id),
                ('state', '=', 'confirmed'),
                ('start_datetime', '<', record.end_datetime),
                ('end_datetime', '>', record.start_datetime),
            ]
            if self.search_count(domain):
                raise ValidationError(_('This time slot is already booked.'))
```

### 5.3 後台選單結構

```
日曆（Calendar）
├── 會議（原有 calendar.event）
├── 資源預約                    # 新增 - booking.reservation 日曆視圖
└── 設定
    ├── 會議類型（原有）
    └── 資源預約類型             # 新增 - booking.resource.type 管理
```

### 5.4 後台視圖設計

#### 資源預約日曆視圖
```xml
<record id="view_booking_reservation_calendar" model="ir.ui.view">
    <field name="name">booking.reservation.calendar</field>
    <field name="model">booking.reservation</field>
    <field name="arch" type="xml">
        <calendar string="Resource Bookings"
                  date_start="start_datetime"
                  date_stop="end_datetime"
                  color="resource_type_id"
                  mode="week"
                  quick_create="0">
            <field name="resource_type_id" filters="1"/>
            <field name="partner_id"/>
        </calendar>
    </field>
</record>
```

### 5.5 控制器設計

#### Portal 控制器
```python
# /my/bookings - 我的預約列表
# /my/bookings/<id> - 預約詳情
# /my/bookings/new - 新增預約（選擇資源）
# /my/bookings/new/<resource_type_id> - 新增指定資源的預約
# /my/bookings/<id>/cancel - 取消預約

# /my/booking/resources - 可預約資源列表（僅顯示被授權的資源）
# /my/booking/resources/<id> - 資源詳情與可用時段
# /my/booking/resources/<id>/slots - 取得可用時段 (JSON API)
```

**權限檢查邏輯**:
```python
def _get_accessible_resources(self, partner):
    """取得該聯絡人可預約的資源"""
    return self.env['booking.resource.type'].sudo().search([
        '|',
        ('share_type', '=', 'all'),
        ('allowed_partner_ids', 'in', [partner.id]),
        ('active', '=', True),
    ])

def _get_slots_for_portal(self, resource_type, date_from, date_to, partner):
    """取得 Portal 用戶可見的時段（隱藏其他人的預約內容）"""
    slots = resource_type._generate_slots(date_from, date_to)
    reservations = self.env['booking.reservation'].sudo().search([
        ('resource_type_id', '=', resource_type.id),
        ('state', '=', 'confirmed'),
        ('start_datetime', '>=', date_from),
        ('end_datetime', '<=', date_to),
    ])

    for slot in slots:
        slot['is_available'] = True
        slot['is_mine'] = False
        for res in reservations:
            if slot['start'] < res.end_datetime and slot['end'] > res.start_datetime:
                slot['is_available'] = False
                if res.partner_id == partner:
                    slot['is_mine'] = True
                    slot['reservation_id'] = res.id
                break
    return slots
```

### 5.6 安全與權限

```xml
<!-- 權限群組 -->
<record id="group_booking_user" model="res.groups">
    <field name="name">Booking User</field>
    <field name="category_id" ref="base.module_category_services"/>
</record>

<record id="group_booking_manager" model="res.groups">
    <field name="name">Booking Manager</field>
    <field name="category_id" ref="base.module_category_services"/>
    <field name="implied_ids" eval="[(4, ref('group_booking_user'))]"/>
</record>

<!-- 存取規則 -->
<!-- booking.reservation -->
<!-- User: 讀取所有已確認預約、CRUD 自己的預約 -->
<!-- Manager: 完整 CRUD 權限 -->
<!-- Portal: 僅能操作自己的預約，只能看到被授權資源 -->
```

---

## 6. 介面設計

### 6.1 後台介面

#### 資源預約頁面（日曆模組下）
- 日曆視圖顯示所有預約
- 資源篩選器（可多選）
- 「新增」按鈕 → 彈出預約表單
- 預約表單欄位：資源、開始時間、結束時間、預約人、備註

#### 資源預約類型設定頁面
- 列表視圖 + 表單視圖
- 表單包含：
  - 基本資訊（名稱、位置、容量、說明、圖片）
  - 時段設定（slot_duration、slot_interval）
  - 可預約時間（週期性時段，One2many）
  - 聯絡人權限（share_type、allowed_partner_ids）
  - 動態屬性（透過「加入屬性」按鈕）

### 6.2 Portal 介面

#### Portal 導航
```
/my/home
├── /my/booking/resources     # 可預約資源列表（僅顯示被授權的資源）
│   └── /my/booking/resources/<id>  # 資源詳情與預約
├── /my/bookings              # 我的預約
│   ├── 列表視圖（預設）
│   └── /my/bookings/new      # 新增預約
├── /my/bookings/<id>         # 預約詳情
└── /my/bookings/<id>/cancel  # 取消預約
```

#### 頁面設計原則
- 使用 Odoo Portal 原生樣式
- 響應式設計，支援手機/平板
- 清晰的狀態指示（顏色標籤）
- 直覺的日期時間選擇器
- 僅顯示用戶被授權預約的資源
- 自訂屬性顯示在資源詳情頁（僅顯示，不可篩選）

#### 資源列表頁面
- 卡片式或列表式顯示可預約資源
- 顯示資源圖片、名稱、位置、容量
- 點擊進入資源詳情與預約頁面

#### 資源詳情與預約頁面
- 顯示資源完整資訊（含自訂屬性）
- 日曆/時段視圖顯示可用時段
- 已預約時段顯示為灰色（不顯示預約人資訊）
- 自己的預約顯示為特殊顏色
- 選擇時段後填寫預約表單

---

## 7. 風險與緩解

| 風險 | 可能性 | 影響 | 緩解策略 |
|------|--------|------|----------|
| 併發預約衝突 | 中 | 高 | 使用資料庫層級鎖定 |
| Portal 效能問題 | 低 | 中 | 分頁載入、快取優化 |
| 權限設定錯誤 | 低 | 中 | 清晰的 UI 提示、預設為指定聯絡人模式 |
| 日曆同步問題 | 低 | 低 | 非同步處理、錯誤重試 |

---

## 8. 時程與里程碑

| 里程碑 | 預估週數 | 交付項目 |
|--------|----------|----------|
| M1: 資料模型 | Week 1-2 | 模型定義、後台視圖、動態屬性支援 |
| M2: 後台功能 | Week 3-4 | 資源管理、時段設定、日曆視圖、篩選器 |
| M3: Portal 介面 | Week 5-7 | Portal 資源列表、預約功能、我的預約 |
| M4: 整合測試 | Week 8 | 測試、修正 |
| M5: 上線準備 | Week 9 | 文件、多語系 |

---

## 9. 已確認決策

| 項目 | 決策 |
|------|------|
| 時段生成方式 | 週期性時段，系統自動根據 slot_duration 生成 |
| 時段間隔 | 可在資源設定中自訂（slot_interval） |
| 選單結構 | 只需「資源預約類型」，整合分類與項目 |
| 資源模型 | 完全獨立，建立新模型 |
| 動態屬性 | 使用 Odoo 原生「加入屬性」功能 |
| 屬性在 Portal | 僅顯示，不可篩選 |
| 後台日曆篩選 | 需要資源篩選器 |
| 最小提前時間 | 不需要 |
| 取消限制 | 不需要 |
| 預約審核 | 不需要，直接確認 |
| 後台/Portal 預約 | 兩者都可以建立預約 |
| 他人預約可見性 | Portal 用戶只能看到「已被預約」，不顯示預約人資訊 |

---

## 10. 附錄

### A. 參考模組

- [WOOWTECH/Odoo_reservation_module](https://github.com/WOOWTECH/Odoo_reservation_module)

### B. Odoo 18 相關文件

- [Odoo 18 開發文件](https://www.odoo.com/documentation/18.0/developer.html)
- [Portal 開發指南](https://www.odoo.com/documentation/18.0/developer/howtos/website.html)
- [Calendar 模組](https://github.com/odoo/odoo/tree/18.0/addons/calendar)

### C. 詞彙表

| 術語 | 說明 |
|------|------|
| Portal 用戶 | 具有 portal.group_portal 權限的外部用戶（聯絡人） |
| 聯絡人權限分享 | 在資源設定中指定哪些聯絡人可預約該資源 |
| 資源預約類型 | 可預約的資源定義（整合原資源類型與資源項目） |
| 授權聯絡人 | 被加入資源 `allowed_partner_ids` 欄位的聯絡人 |
| slot_duration | 每個預約時段的長度（小時） |
| slot_interval | 預約時段之間的間隔（小時） |
