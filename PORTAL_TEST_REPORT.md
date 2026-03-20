# WOOWTECH Odoo 18 Booking Reservation
# Portal 使用者完整功能測試報告

---

## 基本資訊

| 項目 | 說明 |
|------|------|
| **模組名稱** | `odoo_booking_reservation` |
| **測試日期** | 2026-03-20 |
| **Odoo 版本** | 18.0 |
| **測試實例** | odoo-calendar-web (port 9071) |
| **語系** | 繁體中文 (zh_TW) |
| **測試方法** | HTTP Session 模擬 + JSON-RPC + XML-RPC |
| **測試腳本** | `tests/portal_detail_test.py` |

---

## 測試結果總覽

```
╔═══════════════════════════════════════════════════════════╗
║            Portal 完整功能測試結果總覽                      ║
╠═══════════════════════════════════════════════════════════╣
║  總測試數 .............. 66                                ║
║  通過 .................. 66                                ║
║  失敗 .................. 0                                 ║
║  通過率 ................ 100.0%                            ║
╠═══════════════════════════════════════════════════════════╣
║  測試區段: 12 個 (Section 2 ~ Section 13)                  ║
║  全數區段: PASS                                            ║
╚═══════════════════════════════════════════════════════════╝
```

### 各區段通過狀況

| 區段 | 名稱 | 通過 | 總計 | 狀態 |
|------|------|------|------|------|
| 2 | 登入流程 | 5 | 5 | ✅ PASS |
| 3 | Portal 首頁 | 4 | 4 | ✅ PASS |
| 4 | 資源列表頁 | 6 | 6 | ✅ PASS |
| 5 | 資源詳情頁 | 10 | 10 | ✅ PASS |
| 6 | 時段查詢 API | 3 | 3 | ✅ PASS |
| 7 | 建立預約 | 8 | 8 | ✅ PASS |
| 8 | 預約列表頁 | 7 | 7 | ✅ PASS |
| 9 | 預約詳情頁 | 7 | 7 | ✅ PASS |
| 10 | 取消預約 | 5 | 5 | ✅ PASS |
| 11 | RPC 隱私隔離 | 5 | 5 | ✅ PASS |
| 12 | 未登入存取保護 | 3 | 3 | ✅ PASS |
| 13 | 響應式設計 | 3 | 3 | ✅ PASS |

---

## Portal 使用者帳號

| 帳號 | 密碼 | User ID | Partner ID | 說明 |
|------|------|---------|------------|------|
| `portal1` | `portal1` | 8 | 9 | Portal 使用者 (可存取 VIP Room) |
| `portal2` | `portal2` | 9 | 10 | Portal 使用者 (可存取 VIP Room) |
| `portal3` | `portal3` | 10 | 11 | Portal 使用者 (受限，無 VIP) |
| `admin` | `admin` | 2 | 3 | 系統管理員 (後台管理) |

- **登入網址**: `http://localhost:9071/web/login`
- **語系**: 繁體中文 (zh_TW)
- **Portal 入口**: 登入後自動導向 `/my`

---

## 詳細測試結果

### Section 2: Portal 登入流程 (5/5 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 2.1 | 登入頁面載入 | ✅ PASS | HTTP 200，登入表單正常，CSRF token 存在 |
| 2.2-portal1 | portal1 登入成功 | ✅ PASS | 登入後導向 `/my`，HTTP 200 |
| 2.2-portal2 | portal2 登入成功 | ✅ PASS | 登入後導向 `/my`，HTTP 200 |
| 2.2-portal3 | portal3 登入成功 | ✅ PASS | 登入後導向 `/my`，HTTP 200 |
| 2.3 | 錯誤密碼登入被拒絕 | ✅ PASS | 停留在 `/web/login`，顯示錯誤訊息 |

**測試說明：**
- 驗證 `/web/login` 頁面正常載入並包含 CSRF 保護
- 三個 Portal 帳號均能成功登入並被正確導向 Portal 首頁
- 錯誤密碼被正確拒絕，使用者停留在登入頁面且有錯誤提示

---

### Section 3: Portal 首頁 /my (4/4 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 3.1 | Portal 首頁載入 | ✅ PASS | HTTP 200，頁面大小 20,925 bytes |
| 3.2 | 首頁包含預約相關連結 | ✅ PASS | 找到 `/my/booking` 或 `/my/bookings` 連結 |
| 3.3 | 首頁包含中文內容 | ✅ PASS | 11 個中文片段：「跳至內容」「我的帳戶」「登出」等 |
| 3.4 | 導航列包含帳戶/登出 | ✅ PASS | 「我的帳戶」連結存在，「登出」連結存在 |

**測試說明：**
- Portal 首頁能正常載入
- 包含預約系統入口連結
- 繁體中文翻譯正確顯示
- 導航列有完整的帳戶管理和登出功能

---

### Section 4: 資源列表頁 /my/booking/resources (6/6 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 4.1 | 資源列表頁載入 | ✅ PASS | HTTP 200，頁面 12,517 bytes |
| 4.2 | 顯示所有公開資源 (share_type=all) | ✅ PASS | Conference Room A ✓, Small Meeting Room B ✓, Projector ✓, Phone Booth ✓ |
| 4.3 | 顯示 portal1 可存取的限定資源 | ✅ PASS | VIP Room C 可見 |
| 4.4 | 資源卡片包含基本資訊 | ✅ PASS | 卡片樣式正確，含容量/地點資訊 |
| 4.5 | 每個資源有詳情連結 | ✅ PASS | 5 個資源連結 (IDs: 2,3,4,5,6) |
| 4.6 | portal3 不可見 VIP Room C | ✅ PASS | `share_type=specific` 存取控制生效 |

**測試說明：**
- 資源列表正確顯示 5 個可用資源
- `share_type=all` 的公開資源對所有 Portal 使用者可見
- `share_type=specific` 的 VIP Room C 僅對允許清單內的使用者可見 (portal1, portal2)
- portal3 不在 VIP Room C 的允許清單中，確實無法看到此資源

**資源清單：**

| 資源 | ID | 時段長度 | 共享類型 | 位置 |
|------|----|---------|---------|------|
| Conference Room A | 2 | 60 分鐘 | all (公開) | 3F, Building A |
| Small Meeting Room B | 3 | 30 分鐘 | all (公開) | 1F, Building B |
| VIP Room C | 4 | 120 分鐘 | specific (限定) | 5F, Building A |
| Projector | 5 | 60 分鐘 | all (公開) | - |
| Phone Booth | 6 | 15 分鐘 | all (公開) | 1F, Building B |

---

### Section 5: 資源詳情頁 /my/booking/resources/<id> (10/10 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 5.1 | Conference Room A 詳情頁載入 | ✅ PASS | HTTP 200，71,747 bytes |
| 5.2 | 詳情頁包含資源名稱和預約功能 | ✅ PASS | 資源名稱正確，有時段選擇和預約功能 |
| 5.3 | 顯示可選擇的時段按鈕 | ✅ PASS | 約 116 個時段按鈕 |
| 5.4 | 有日期選擇功能 | ✅ PASS | 日期選擇器存在 |
| 5.5 | Small Meeting Room B 詳情頁 | ✅ PASS | 30 分鐘時段資源正常 |
| 5.6 | portal1 可存取 VIP Room C | ✅ PASS | HTTP 200 |
| 5.7 | portal3 不可存取 VIP Room C | ✅ PASS | HTTP 403 (正確拒絕) |
| 5.8 | 不存在的資源回傳友善錯誤 | ✅ PASS | HTTP 400 (非 500) |
| 5.9 | Projector 詳情頁 | ✅ PASS | HTTP 200 |
| 5.10 | Phone Booth 詳情頁 (15min slots) | ✅ PASS | HTTP 200 |

**測試說明：**
- 每個資源的詳情頁都包含完整資訊：名稱、說明、時段按鈕、日期選擇
- Conference Room A 的 60 分鐘時段產生約 49 個預約表單 (每日 7am-12am)
- 存取控制正確：portal3 存取 VIP Room C 回傳 403
- 不存在的資源 (ID=99999) 回傳 400 而非 500（BUG-002 修復驗證）

---

### Section 6: 時段查詢 API (3/3 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 6.1 | Conference Room A 時段查詢 | ✅ PASS | HTTP 200，Content-Type: application/json |
| 6.2 | 時段 API 返回 JSON 格式 | ✅ PASS | 209 個時段，dict 格式 |
| 6.3 | Small Meeting Room B 時段查詢 | ✅ PASS | 198 個時段 (30min intervals) |

**技術說明：**
- 時段 API 路由 `/my/booking/resources/<id>/slots` 使用 Odoo `type='json'`
- 呼叫方式為 JSON-RPC (`Content-Type: application/json`，含 `jsonrpc: "2.0"` 信封)
- Conference Room A (60min) 回傳 209 個可用時段
- Small Meeting Room B (30min) 回傳 198 個可用時段
- 時段數量差異來自不同的 slot interval 設定

---

### Section 7: 建立預約流程 (8/8 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 7.1 | 新預約頁面載入 | ✅ PASS | `/my/bookings/new` 為資源選擇頁 |
| 7.2 | 建立預約 - Conference Room A | ✅ PASS | booking_id=282，導向 `?success=created` |
| 7.3 | 建立預約 - Small Meeting Room B | ✅ PASS | booking_id=283 |
| 7.4 | 建立預約 - VIP Room C (portal1) | ✅ PASS | booking_id=284 |
| 7.5 | portal3 預約 VIP Room C 被拒絕 | ✅ PASS | 導向 `?error=unauthorized` |
| 7.6 | 空白表單提交被友善處理 | ✅ PASS | 導向 `?error=missing_fields` |
| 7.7 | 無效 resource_id 被友善處理 | ✅ PASS | 導向 `?error=invalid_resource` |
| 7.8 | portal2 建立預約成功 | ✅ PASS | booking_id=285 |

**預約建立流程：**
1. 使用者訪問 `/my/bookings/new` → 資源選擇頁面
2. 選擇資源 → 導向 `/my/booking/resources/<id>` 資源詳情頁
3. 選擇日期 → 頁面顯示可用時段按鈕
4. 點擊時段按鈕 → 自動 POST 到 `/my/bookings/create`
5. 成功 → 導向 `/my/bookings/<id>?success=created`
6. 失敗 → 導向 `/my/bookings/new?error=<reason>`

**錯誤處理驗證：**
- `error=unauthorized`：portal3 嘗試預約不在允許清單的資源
- `error=missing_fields`：空白表單提交
- `error=invalid_resource`：resource_id=99999 不存在

---

### Section 8: 預約列表頁 /my/bookings (7/7 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 8.1 | 預約列表頁載入 | ✅ PASS | HTTP 200，15,330 bytes |
| 8.2 | 預約列表包含預約記錄 | ✅ PASS | 有 booking 記錄 |
| 8.3 | 預約狀態徽章顯示 | ✅ PASS | confirmed 狀態正確，badge 樣式正確 |
| 8.4 | 列表有篩選/排序功能 | ✅ PASS | 篩選功能存在 |
| 8.5 | 依狀態篩選 (confirmed) | ✅ PASS | `?filterby=confirmed` 正常 |
| 8.6 | 依日期排序 | ✅ PASS | `?sortby=date` 正常 |
| 8.7 | portal2 只看到自己的預約 | ✅ PASS | portal1 的預約不可見 |

**隱私隔離驗證：**
- portal2 只能看到自己建立的預約記錄
- portal1 的預約備註 ("Portal 細部測試預約 - Conference Room A") 在 portal2 的列表中不可見
- 此驗證證明 ir.rule 記錄規則在 Portal 頁面正確運作

---

### Section 9: 預約詳情頁 /my/bookings/<id> (7/7 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 9.1 | 預約詳情頁載入 (id=282) | ✅ PASS | HTTP 200 |
| 9.2 | 詳情頁包含資源名稱 | ✅ PASS | Conference Room A 正確顯示 |
| 9.3 | 詳情頁包含預約時間 | ✅ PASS | 時間 10:00 正確顯示 |
| 9.4 | 詳情頁包含備註 | ✅ PASS | 備註內容正確 |
| 9.5 | 詳情頁顯示狀態 | ✅ PASS | confirmed 狀態正確 |
| 9.6 | 詳情頁有取消按鈕 | ✅ PASS | 取消按鈕存在 |
| 9.7 | portal2 不能查看 portal1 的預約 | ✅ PASS | HTTP 400 正確拒絕 |

**測試說明：**
- 預約詳情頁完整顯示：資源名稱、時間、備註、狀態
- 取消按鈕在 confirmed 狀態的預約上可見
- 跨用戶存取被正確阻擋 (HTTP 400)

---

### Section 10: 取消預約 (5/5 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 10.1 | 預約詳情頁有取消動作 (id=283) | ✅ PASS | `/my/bookings/283/cancel` 存在 |
| 10.2 | 取消預約成功 | ✅ PASS | 導向 `?success=cancelled` |
| 10.3 | 取消後狀態顯示為 cancelled | ✅ PASS | 頁面顯示 cancelled |
| 10.4 | RPC 確認預約狀態 | ✅ PASS | `state=cancelled` |
| 10.5 | portal2 不能取消 portal1 的預約 | ✅ PASS | HTTP 400 正確拒絕 |

**取消流程：**
1. 在預約詳情頁點擊「取消」按鈕
2. POST 到 `/my/bookings/<id>/cancel` (含 CSRF token)
3. 成功 → 導向 `?success=cancelled`
4. 狀態由 `confirmed` 變為 `cancelled`

**安全驗證：**
- portal2 嘗試取消 portal1 的預約 (id=282) 被拒絕 (HTTP 400)
- 跨用戶取消操作被正確阻擋

---

### Section 11: XML-RPC 隱私隔離驗證 (5/5 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 11.1 | portal1 搜尋預約 | ✅ PASS | 只能看到 23 筆自己的預約 |
| 11.2 | portal2 搜尋預約 | ✅ PASS | 只能看到 14 筆自己的預約 |
| 11.3 | portal1 不能讀取 portal2 的預約 | ✅ PASS | AccessError (Fault) |
| 11.4 | portal2 不能修改 portal1 的預約 | ✅ PASS | AccessError (Fault) |
| 11.5 | portal1 可讀取自己的預約 | ✅ PASS | state=confirmed, note 正確 |

**ir.rule 記錄規則驗證：**
```xml
<!-- Portal 使用者只能存取自己的預約 -->
<record id="booking_reservation_portal_rule" model="ir.rule">
    <field name="domain_force">[('partner_id', '=', user.partner_id.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_portal'))]"/>
</record>
```

- portal1 搜尋 `booking.reservation` → 只回傳 partner_id=9 的記錄 (23 筆)
- portal2 搜尋 → 只回傳 partner_id=10 的記錄 (14 筆)
- portal1 嘗試讀取 portal2 的預約 (id=285) → `AccessError`
- portal2 嘗試修改 portal1 的預約 (id=282) → `AccessError`
- portal1 讀取自己的預約 → 正常回傳完整資料

---

### Section 12: 未登入存取保護 (3/3 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 12.1 | 未登入存取資源列表 | ✅ PASS | 303 → `/web/login?redirect=...` |
| 12.2 | 未登入存取預約列表 | ✅ PASS | 303 → `/web/login?redirect=...` |
| 12.3 | 未登入存取新建預約 | ✅ PASS | 303 → `/web/login?redirect=...` |

**測試說明：**
- 所有 Portal 路由都設定 `auth='user'`
- 未登入的匿名使用者嘗試存取任何 Portal 頁面都會被 303 重導到登入頁
- 重導 URL 包含 `redirect` 參數，登入後可返回原頁面

**受保護的路由：**
| 路由 | 用途 |
|------|------|
| `/my/booking/resources` | 資源列表 |
| `/my/booking/resources/<id>` | 資源詳情 |
| `/my/booking/resources/<id>/slots` | 時段 API |
| `/my/bookings` | 預約列表 |
| `/my/bookings/new` | 新建預約 |
| `/my/bookings/<id>` | 預約詳情 |
| `/my/bookings/create` | 建立預約 (POST) |
| `/my/bookings/<id>/cancel` | 取消預約 (POST) |

---

### Section 13: 響應式設計 (3/3 PASS)

| 測試 ID | 測試項目 | 結果 | 細節 |
|---------|---------|------|------|
| 13.1 | 資源列表 (手機) | ✅ PASS | 含 viewport meta，12,517 bytes |
| 13.2 | 資源詳情 (手機) | ✅ PASS | 含 viewport meta，70,524 bytes |
| 13.3 | 預約列表 (手機) | ✅ PASS | 含 viewport meta，13,932 bytes |

**測試說明：**
- 使用 iPhone Safari User-Agent 模擬手機瀏覽
- 所有頁面都包含 `viewport` meta 標籤
- 使用 Bootstrap 響應式框架，自動適應螢幕尺寸

---

## Portal 功能架構圖

```
┌──────────────────────────────────────────────────────────────┐
│                     Portal 功能架構                           │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  /web/login ─────────────► /my (首頁)                        │
│       │                      │                               │
│       │ CSRF + password      ├── /my/booking/resources       │
│       │                      │      │                        │
│       ▼                      │      ├── /resources/<id>      │
│   登入失敗 → 錯誤訊息        │      │     │                  │
│                              │      │     ├── /slots (JSON)  │
│                              │      │     └── 選擇時段       │
│                              │      │            │           │
│                              │      │            ▼           │
│                              │      │     /bookings/create   │
│                              │      │        (POST+CSRF)     │
│                              │      │            │           │
│                              │      │     ┌──────┴──────┐    │
│                              │      │     ▼             ▼    │
│                              │  /my/bookings     ?error=xxx  │
│                              │      │                        │
│                              │      ├── /<id> (詳情)         │
│                              │      │     │                  │
│                              │      │     └── /cancel (POST) │
│                              │      │            │           │
│                              │      │     ┌──────┴──────┐    │
│                              │      │     ▼             ▼    │
│                              │      │  cancelled    error    │
│                              │                               │
│                              └── /my/bookings/new            │
│                                    (資源選擇頁)               │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## 安全機制總覽

### 1. 認證層 (Authentication)
- 所有 Portal 路由使用 `auth='user'`
- 未登入使用者自動導向 `/web/login`
- 登入使用 CSRF token 保護

### 2. CSRF 保護 (Cross-Site Request Forgery)
- 所有 POST 路由自動驗證 `csrf_token`
- Token 嵌入在每個表單的 hidden input 中
- JSON-RPC 路由 (`type='json'`) 由 Content-Type 限制保護

### 3. ACL 存取控制 (ir.model.access)
```
Portal 使用者對 booking.reservation 的 ACL：
  Read: ✅  Write: ✅  Create: ✅  Unlink: ❌
```

### 4. 記錄規則 (ir.rule) - 行級存取控制
```
Portal 規則：[('partner_id', '=', user.partner_id.id)]
→ 每個 Portal 使用者只能存取自己的預約記錄
```

### 5. 資源存取控制 (share_type)
- `share_type=all`：所有使用者可見
- `share_type=specific`：僅允許清單內的使用者可見
- Controller 層檢查 `_check_resource_access()`

### 6. 錯誤處理
| 錯誤類型 | 處理方式 |
|---------|---------|
| 無效 resource_id | 導向 `?error=invalid_resource` |
| 未授權資源 | 導向 `?error=unauthorized` |
| 缺少必填欄位 | 導向 `?error=missing_fields` |
| 跨用戶存取 | HTTP 400 |
| 不存在的預約 | HTTP 400 |

---

## 測試涵蓋的完整路由

| # | 路由 | 方法 | Type | 測試區段 |
|---|------|------|------|---------|
| 1 | `/web/login` | GET/POST | http | Section 2 |
| 2 | `/my` | GET | http | Section 3 |
| 3 | `/my/booking/resources` | GET | http | Section 4 |
| 4 | `/my/booking/resources/<id>` | GET | http | Section 5 |
| 5 | `/my/booking/resources/<id>/slots` | POST (JSON-RPC) | json | Section 6 |
| 6 | `/my/bookings/new` | GET | http | Section 7 |
| 7 | `/my/bookings/create` | POST | http | Section 7 |
| 8 | `/my/bookings` | GET | http | Section 8 |
| 9 | `/my/bookings/<id>` | GET | http | Section 9 |
| 10 | `/my/bookings/<id>/cancel` | POST | http | Section 10 |

---

## 測試數據

測試過程中建立的預約記錄：

| 預約 ID | 使用者 | 資源 | 狀態 |
|---------|--------|------|------|
| 282 | portal1 | Conference Room A | confirmed |
| 283 | portal1 | Small Meeting Room B | cancelled (測試取消) |
| 284 | portal1 | VIP Room C | confirmed |
| 285 | portal2 | Conference Room A | confirmed |

---

## 結論

Portal 使用者功能經過 12 個區段、66 項測試的全面驗證，**全部通過 (100%)**。

**功能完整性：**
- 完整的預約生命週期：瀏覽資源 → 選擇時段 → 建立預約 → 查看列表/詳情 → 取消預約
- 資源存取控制正確 (share_type=all / specific)
- 時段查詢 API 正常運作 (JSON-RPC)
- 篩選和排序功能正常

**安全性：**
- 認證保護完整（未登入重導）
- CSRF 保護生效
- ir.rule 記錄隔離確保跨用戶資料不可見
- 錯誤輸入處理完善（無 500 錯誤）

**使用者體驗：**
- 繁體中文正確顯示
- 響應式設計支援手機瀏覽
- 清楚的成功/錯誤提示訊息
- 友善的導航結構

---

*報告產生日期: 2026-03-20*
*測試腳本: `tests/portal_detail_test.py`*
*測試實例: odoo-calendar-web (port 9071)*
