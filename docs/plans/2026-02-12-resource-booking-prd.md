# Odoo 18 資源預約模組 PRD

**文件版本**: 1.0
**日期**: 2026-02-12
**狀態**: Draft
**模組名稱**: `booking_reservation`

---

## 1. 執行摘要

### 問題陳述
Odoo 18 Community 版本的日曆功能缺乏完整的資源預約管理能力，無法讓 Portal 用戶自主預約會議室或其他共享資源，企業需要額外的解決方案來管理內部資源預約需求。

### 提案解決方案
開發一個獨立的資源預約模組，擴展 Odoo 18 日曆功能，支援 Portal 用戶透過 Portal 介面預約資源，並提供外部分享連結功能，且不依賴網站 (website) 模組。

### 業務影響
- 提升內部資源使用效率，減少預約衝突
- 讓外部合作夥伴或訪客可透過分享連結預約資源
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
| **Who** | 企業內部員工、Portal 用戶、外部訪客 |
| **What** | 無法透過 Portal 預約會議室/資源，缺乏外部分享機制 |
| **When** | 日常會議安排、訪客來訪、跨部門協作時 |
| **Where** | Odoo Portal 介面、分享連結頁面 |
| **Why** | Odoo 18 Community 日曆功能未提供 Portal 資源預約能力 |
| **Impact** | 手動協調耗時、預約衝突頻繁、資源使用率低 |

### 2.2 業務案例
- **策略價值**: 強化 Odoo 生態系統的協作能力
- **效率提升**: 減少人工協調時間 50%+
- **獨立部署**: 不依賴 website 模組，適合僅使用後台的企業

---

## 3. 解決方案概覽

### 3.1 提案解決方案

基於 Odoo 18 的日曆 (calendar) 和資源 (resource) 模組，開發獨立的資源預約模組，核心功能包括：

1. **資源預約管理** - 後台管理可預約的資源（會議室、設備等）
2. **Portal 預約介面** - Portal 用戶可在 Portal 頁面建立/查看/取消預約
3. **外部分享連結** - 生成分享連結讓非系統用戶也能預約
4. **預約衝突檢測** - 自動檢測並防止時間衝突
5. **通知系統** - 預約確認、提醒、取消通知

### 3.2 範圍內 (In Scope)

| 功能 | 優先級 | 說明 |
|------|--------|------|
| 資源類型管理 | P0 | 定義可預約資源類型（會議室、設備等） |
| 資源項目管理 | P0 | 管理具體資源（1號會議室、投影機等） |
| 預約時段設定 | P0 | 設定資源可預約時間範圍 |
| Portal 預約介面 | P0 | Portal 用戶預約頁面 |
| 外部分享連結 | P0 | 生成公開預約連結 |
| 預約衝突檢測 | P0 | 防止重複預約 |
| 電子郵件通知 | P1 | 預約確認/提醒通知 |
| 預約審核流程 | P1 | 可選的預約審核機制 |
| 日曆整合 | P1 | 與 Odoo 日曆事件同步 |
| 多語系支援 | P2 | 繁體中文、簡體中文、英文 |

### 3.3 範圍外 (Out of Scope)

- 付費預約功能（需整合付款模組）
- 網站前台頁面（本模組不依賴 website 模組）
- 視訊會議整合
- 餐桌預訂等特定行業功能
- 員工行程預約功能

### 3.4 MVP 定義

**核心功能集**:
1. 資源類型與資源項目的 CRUD
2. 預約時段設定（可預約時間範圍）
3. Portal 用戶預約介面（列表、日曆視圖）
4. 外部分享連結生成
5. 基本預約衝突檢測

**成功標準**:
- Portal 用戶可完成完整預約流程
- 外部用戶可透過分享連結預約
- 系統正確阻擋衝突預約

---

## 4. 用戶故事與需求

### 4.1 用戶故事

#### US-001: 資源管理員建立可預約資源
```
作為 資源管理員
我想要 在後台建立和管理可預約的資源
以便 讓用戶可以預約這些資源

驗收條件:
- [ ] 可建立資源類型（如：會議室、設備）
- [ ] 可建立資源項目並指定類型
- [ ] 可設定資源的可預約時段
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

#### US-003: 管理員生成外部分享連結
```
作為 資源管理員
我想要 為資源生成外部分享連結
以便 讓非系統用戶也能預約資源

驗收條件:
- [ ] 可為資源生成唯一的分享連結
- [ ] 可設定連結的有效期限
- [ ] 可設定是否需要填寫聯絡資訊
- [ ] 可停用分享連結
```

#### US-004: 外部用戶透過分享連結預約
```
作為 外部訪客
我想要 透過分享連結預約資源
以便 安排我的訪問或會議

驗收條件:
- [ ] 無需登入即可存取分享連結頁面
- [ ] 可查看資源可用時段
- [ ] 可填寫必要資訊完成預約
- [ ] 預約成功後收到確認郵件
```

#### US-005: 系統防止預約衝突
```
作為 系統
我需要 自動檢測預約時間衝突
以便 確保資源不會被重複預約

驗收條件:
- [ ] 選擇時段時顯示已被預約的時間
- [ ] 提交衝突預約時顯示錯誤訊息
- [ ] 並發預約時正確處理競爭條件
```

### 4.2 功能需求

| ID | 需求 | 優先級 | 備註 |
|----|------|--------|------|
| FR-001 | 資源類型 CRUD | P0 | 後台管理 |
| FR-002 | 資源項目 CRUD | P0 | 含圖片、說明、容量 |
| FR-003 | 可預約時段設定 | P0 | 週期性時段設定 |
| FR-004 | Portal 資源列表頁 | P0 | 響應式設計 |
| FR-005 | Portal 預約表單 | P0 | 日期時間選擇器 |
| FR-006 | Portal 我的預約頁 | P0 | 列表與日曆視圖 |
| FR-007 | 外部分享連結生成 | P0 | 含有效期設定 |
| FR-008 | 外部預約頁面 | P0 | 無需登入 |
| FR-009 | 預約衝突檢測 | P0 | 即時檢測 |
| FR-010 | 預約狀態管理 | P1 | 待確認/已確認/已取消 |
| FR-011 | 郵件通知 | P1 | 確認/提醒/取消 |
| FR-012 | 預約審核 | P1 | 可選功能 |
| FR-013 | 日曆事件同步 | P1 | calendar.event |
| FR-014 | 報表統計 | P2 | 使用率統計 |

### 4.3 非功能需求

| 類型 | 需求 |
|------|------|
| **效能** | 預約列表載入 < 2 秒 |
| **並發** | 支援 100+ 同時預約操作 |
| **安全** | Portal 用戶只能操作自己的預約 |
| **相容性** | Odoo 18 Community Edition |
| **獨立性** | 不依賴 website 模組 |
| **多語系** | 支援 en_US, zh_TW, zh_CN |

---

## 5. 技術規格

### 5.1 模組相依性

```python
'depends': ['base', 'mail', 'calendar', 'resource', 'portal'],
```

**說明**:
- `base`: Odoo 核心
- `mail`: 郵件通知功能
- `calendar`: 日曆整合
- `resource`: 資源管理基礎
- `portal`: Portal 用戶介面

**不依賴**: `website`（關鍵設計決策）

### 5.2 資料模型

#### booking.resource.type（資源類型）
```python
class BookingResourceType(models.Model):
    _name = 'booking.resource.type'
    _description = 'Booking Resource Type'

    name = fields.Char(required=True, translate=True)
    description = fields.Text(translate=True)
    icon = fields.Char()
    active = fields.Boolean(default=True)
    resource_ids = fields.One2many('booking.resource', 'type_id')
```

#### booking.resource（可預約資源）
```python
class BookingResource(models.Model):
    _name = 'booking.resource'
    _description = 'Bookable Resource'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(required=True, translate=True)
    type_id = fields.Many2one('booking.resource.type', required=True)
    description = fields.Html(translate=True)
    image = fields.Image()
    capacity = fields.Integer(default=1)
    location = fields.Char()
    active = fields.Boolean(default=True)

    # 可預約時段設定
    availability_ids = fields.One2many('booking.resource.availability', 'resource_id')

    # 外部分享
    share_token = fields.Char(copy=False)
    share_expiry = fields.Datetime()
    share_require_contact = fields.Boolean(default=True)

    # 預約設定
    min_duration = fields.Float(default=0.5)  # 小時
    max_duration = fields.Float(default=8.0)
    advance_days = fields.Integer(default=30)  # 可提前預約天數
    approval_required = fields.Boolean(default=False)
```

#### booking.resource.availability（可預約時段）
```python
class BookingResourceAvailability(models.Model):
    _name = 'booking.resource.availability'
    _description = 'Resource Availability'

    resource_id = fields.Many2one('booking.resource', required=True, ondelete='cascade')
    dayofweek = fields.Selection([
        ('0', 'Monday'), ('1', 'Tuesday'), ('2', 'Wednesday'),
        ('3', 'Thursday'), ('4', 'Friday'), ('5', 'Saturday'), ('6', 'Sunday')
    ], required=True)
    hour_from = fields.Float(required=True)
    hour_to = fields.Float(required=True)
```

#### booking.reservation（預約記錄）
```python
class BookingReservation(models.Model):
    _name = 'booking.reservation'
    _description = 'Resource Reservation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _order = 'start_datetime desc'

    name = fields.Char(compute='_compute_name', store=True)
    resource_id = fields.Many2one('booking.resource', required=True)

    # 預約時間
    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime(required=True)
    duration = fields.Float(compute='_compute_duration', store=True)

    # 預約人
    partner_id = fields.Many2one('res.partner')  # Portal 用戶
    guest_name = fields.Char()  # 外部訪客
    guest_email = fields.Char()
    guest_phone = fields.Char()

    # 狀態
    state = fields.Selection([
        ('draft', 'Draft'),
        ('pending', 'Pending Approval'),
        ('confirmed', 'Confirmed'),
        ('cancelled', 'Cancelled'),
    ], default='draft', tracking=True)

    # 關聯
    calendar_event_id = fields.Many2one('calendar.event')

    # 備註
    note = fields.Text()

    _sql_constraints = [
        ('check_dates', 'CHECK(end_datetime > start_datetime)',
         'End time must be after start time'),
    ]
```

### 5.3 控制器設計

#### Portal 控制器
```python
# /my/bookings - 我的預約列表
# /my/bookings/<id> - 預約詳情
# /my/bookings/new - 新增預約
# /my/bookings/<id>/cancel - 取消預約
```

#### 外部分享控制器
```python
# /booking/share/<token> - 外部預約頁面
# /booking/share/<token>/submit - 提交預約
# /booking/share/<token>/slots - 取得可用時段 (JSON)
```

### 5.4 安全與權限

```xml
<!-- 權限群組 -->
<record id="group_booking_user" model="res.groups">
    <field name="name">Booking User</field>
</record>

<record id="group_booking_manager" model="res.groups">
    <field name="name">Booking Manager</field>
</record>

<!-- 存取規則 -->
<!-- booking.reservation -->
<!-- User: 讀取所有已確認預約、CRUD 自己的預約 -->
<!-- Manager: 完整 CRUD 權限 -->
<!-- Portal: 僅能操作自己的預約 -->
```

---

## 6. Portal 用戶介面設計

### 6.1 Portal 導航

```
/my/home
├── /my/bookings              # 我的預約
│   ├── 列表視圖（預設）
│   ├── 日曆視圖
│   └── /my/bookings/new      # 新增預約
├── /my/bookings/<id>         # 預約詳情
└── /my/bookings/<id>/cancel  # 取消預約
```

### 6.2 頁面設計原則

- 使用 Odoo Portal 原生樣式
- 響應式設計，支援手機/平板
- 清晰的狀態指示（顏色標籤）
- 直覺的日期時間選擇器

### 6.3 外部分享頁面

- 簡潔的單頁設計
- 無需登入
- 清晰顯示資源資訊
- 視覺化的時段選擇器
- 必要欄位驗證

---

## 7. 風險與緩解

| 風險 | 可能性 | 影響 | 緩解策略 |
|------|--------|------|----------|
| 併發預約衝突 | 中 | 高 | 使用資料庫層級鎖定 |
| Portal 效能問題 | 低 | 中 | 分頁載入、快取優化 |
| 外部連結濫用 | 中 | 中 | 連結有效期、速率限制 |
| 日曆同步問題 | 低 | 低 | 非同步處理、錯誤重試 |

---

## 8. 時程與里程碑

| 里程碑 | 預估週數 | 交付項目 |
|--------|----------|----------|
| M1: 資料模型 | Week 1-2 | 模型定義、後台視圖 |
| M2: 後台功能 | Week 3-4 | 資源管理、時段設定 |
| M3: Portal 介面 | Week 5-6 | Portal 預約功能 |
| M4: 外部分享 | Week 7-8 | 分享連結功能 |
| M5: 整合測試 | Week 9 | 測試、修正 |
| M6: 上線準備 | Week 10 | 文件、多語系 |

---

## 9. 開放問題

1. **預約審核流程**: 是否需要支援多層級審核？
2. **重複預約**: 是否支援週期性重複預約？
3. **取消政策**: 取消是否需要設定最遲取消時限？
4. **容量預約**: 是否支援部分容量預約（如會議室部分座位）？

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
| Portal 用戶 | 具有 portal.group_portal 權限的外部用戶 |
| 外部分享 | 透過唯一連結讓無帳號用戶預約 |
| 資源類型 | 資源分類（如會議室、設備） |
| 資源項目 | 具體可預約的資源實體 |
