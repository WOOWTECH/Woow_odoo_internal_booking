# 商用前測試報告 — Odoo Booking Reservation Module
# Pre-Production Test Report

**模組**: odoo_booking_reservation (WOOWTECH Odoo 18 Internal Booking)
**測試日期**: 2026-03-20
**測試環境**: odoo-calendar (port 9071), PostgreSQL (odoocalendar)
**Odoo 版本**: 18.0
**語系**: zh_TW (繁體中文)
**來源**: https://github.com/WOOWTECH/Woow_odoo_internal_booking (branch: vk/9074-)

---

## 總覽 Executive Summary

| 指標 | 數值 |
|------|------|
| **總測試數** | 162 |
| **通過** | 157 |
| **失敗** | 5 |
| **通過率** | 96.9% |
| **嚴重缺陷** | 1 (HIGH) |
| **中等缺陷** | 1 (MEDIUM) |
| **已修復缺陷** | 1 (安裝時的 XML 檢視順序) |

### 結論

模組核心功能穩定，CRUD 操作、權限控制 (ACL)、重複預約偵測、資料驗證等均正常運作。**但發現一個高嚴重度安全漏洞：Portal 使用者可透過 XML-RPC 讀取及修改其他使用者的預約記錄（缺少 `ir.rule` 記錄規則）。此問題必須在上線前修復。**

---

## 測試結果摘要

| Phase | 測試項目 | 測試數 | 通過 | 失敗 | 通過率 |
|-------|---------|-------|------|------|--------|
| Phase 1 | 後台管理員 CRUD | 23 | 23 | 0 | 100% |
| Phase 2 | 內部使用者權限 | 11 | 11 | 0 | 100% |
| Phase 3 | Portal 使用者 | 34 | 32 | 2 | 94.1% |
| Phase 4 | 邊緣事件與衝突 | 29 | 29 | 0 | 100% |
| Phase 5 | 壓力測試 | 11 | 11 | 0 | 100% |
| Phase 6 | 安全性測試 | 24 | 23 | 1 | 95.8% |
| Phase 7 | UI/UX 與多語系 | 30 | 28 | 2 | 93.3% |
| **合計** | | **162** | **157** | **5** | **96.9%** |

---

## Phase 1: 後台管理員 (Manager) CRUD 測試 — 23/23 PASS

以 `test_manager` (Booking Manager 群組) 身份執行。

### 1.1 資源類別 CRUD (4/4)
- CREATE: 建立新類別 ✓
- READ: 讀取類別資料 ✓
- UPDATE: 修改類別名稱 ✓
- DELETE: 刪除類別 ✓

### 1.2 資源類型 CRUD (6/6)
- CREATE: 建立含完整屬性的資源 ✓
- READ: 讀取資源（含 capacity, location, slot_duration）✓
- UPDATE: 修改容量/時段/位置 ✓
- ARCHIVE: 停用資源 (active=False) ✓
- UNARCHIVE: 啟用資源 (active=True) ✓
- DELETE: 刪除資源 ✓

### 1.3 預約管理 CRUD (6/6)
- CREATE: 建立預約（自動產生名稱、確認狀態）✓
- READ: 讀取預約（computed fields: name, duration, state）✓
- UPDATE: 修改備註、結束時間 ✓
- action_cancel: 取消預約 → state=cancelled ✓
- action_confirm: 重新確認 → state=confirmed ✓
- DELETE: 刪除預約 ✓

### 1.4 搜尋與篩選 (3/3)
- 依資源名稱搜尋 (ilike 'Conference') ✓
- 依狀態篩選 (state='confirmed') ✓
- 依合作夥伴篩選 (partner_id) ✓

### 1.5 可用時間 CRUD (4/4)
- CREATE/READ/UPDATE/DELETE 全部通過 ✓

---

## Phase 2: 內部使用者 (User) 權限測試 — 11/11 PASS

以 `test_user` (Booking User 群組) 身份執行。

### 允許的操作 (3/3)
- CAN 讀取資源類型 (5 筆資源) ✓
- CAN 建立自己的預約 ✓
- CAN 讀取自己的預約 ✓

### 禁止的操作 (7/7)
- CANNOT 建立/修改/刪除 資源類別 (AccessError, faultCode=4) ✓
- CANNOT 建立/修改/刪除 資源類型 (AccessError, faultCode=4) ✓
- CANNOT 刪除預約 (AccessError, faultCode=4) ✓

### 自身預約操作 (1/1)
- CAN 取消自己的預約 (action_cancel) ✓

---

## Phase 3: Portal 使用者測試 — 32/34 (2 FAIL)

以 `portal1`, `portal2`, `portal3` 身份執行。

### Section A: XML-RPC 權限 (16/16 PASS)
- 三個 Portal 使用者均成功驗證 ✓
- CAN 讀取資源類型、類別、可用時間 ✓
- CANNOT 建立/修改/刪除 資源類型和類別 ✓
- CAN 建立預約、修改自己的預約 ✓
- CANNOT 刪除預約 ✓
- CAN 取消自己的預約 ✓

### Section B: 存取控制 (6/6 PASS)
- portal1 CAN 預約 VIP Room C (share_type=specific, 在允許名單) ✓
- portal2 CAN 預約 VIP Room C (在允許名單) ✓
- portal3 CANNOT 預約 VIP Room C (不在允許名單) ✓
- 三個 Portal 使用者均 CAN 預約 Conference Room A (share_type=all) ✓

### Section C: HTTP 路由 (7/7 PASS)
- POST /web/login 登入 ✓
- GET /my/booking/resources 資源列表 ✓
- GET /my/booking/resources/2 資源詳情 ✓
- GET /my/bookings 預約列表 ✓
- POST /my/bookings/create 建立預約 ✓
- GET /my/bookings/{id} 預約詳情 ✓
- POST /my/bookings/{id}/cancel 取消預約 ✓

### Section D: 隱私保護 (3/5, 2 FAIL) ⚠️

| 測試 | 結果 | 說明 |
|------|------|------|
| D1: portal1 建立預約 | PASS | id=164 |
| D2: portal2 建立預約 | PASS | id=165 |
| **D3a: portal1 透過 RPC 讀取 portal2 的預約** | **FAIL** | **可以讀取（partner_id=[10, 'Portal User 2']）** |
| **D3b: portal1 透過 RPC 修改 portal2 的預約** | **FAIL** | **可以修改成功（無隔離）** |
| D3c: portal1 透過 HTTP 查看 portal2 的預約 | PASS | HTTP 回傳 400（正確阻擋）|

---

## Phase 4: 邊緣事件與衝突偵測 — 29/29 PASS

### 1. 重複預約偵測 (5/5)
- 完全重疊 → 正確拒絕 ✓
- 部分重疊 (10:30-11:30) → 正確拒絕 ✓
- 不同房間同時段 → 正確允許 ✓
- 相鄰時段 (11:00-12:00) → 正確允許 ✓

### 2. 日期時間驗證 (3/3)
- 結束時間早於開始時間 → 拒絕 ✓
- 結束時間等於開始時間 → 拒絕 ✓
- 極短預約 (1 分鐘) → 允許 ✓

### 3. 資源狀態 (3/3)
- 停用資源 → active=False ✓
- 預約已停用資源 → 後台允許 (admin override) ✓
- 重新啟用資源 → active=True ✓

### 4. 取消後重新預約 (3/3)
- 取消預約 → state=cancelled ✓
- 重新預約同時段 → 正確允許 ✓
- 重新確認已取消的預約（有重疊）→ 正確拒絕 ✓

### 5. 時段長度邊緣 (2/2)
- 不匹配時段 (45min on 1h-slot) → 後台允許 ✓
- 超長預約 (8 小時) → 允許 ✓

### 6. advance_days 測試 (3/3)
- advance_days=0 → 正確拒絕 (constraint violation) ✓
- advance_days=1 → 設定成功 ✓
- 預約超過 advance_days → 後台允許 (僅 Portal 端驗證) ✓

### 7. 約束條件驗證 (5/5)
- slot_duration=0 → 拒絕 ✓
- slot_interval=0 → 拒絕 ✓
- slot_duration=-1 → 拒絕 ✓
- hour_from > hour_to → 拒絕 ✓
- hour_from=25 → 拒絕 ✓

### 8. 快速連續預約 (2/2)
- 連續建立 10 個 30 分鐘預約 → 全部成功 ✓
- 插入重疊時段 → 正確拒絕 ✓

### 9. 週末可用時間 (3/3)
- 週六預約 (有設定可用時間) → 允許 ✓
- 週日無可用時間設定 → 確認 ✓
- 週日預約 → 後台允許 (可用時間僅為 Portal 端篩選) ✓

---

## Phase 5: 壓力測試 — 11/11 PASS

### 5.1 大量資源建立
- 建立 100 個資源: **3.27 秒** ✓
- 清理 100 個資源: 全部移除 ✓

### 5.2 大量預約建立
- 建立 50 個預約: **2.03 秒** ✓

### 5.3 快速建立/取消
- 建立+取消 20 個預約: **2.21 秒**, 20/20 取消成功 ✓

### 5.4 搜尋效能
| 搜尋類型 | 結果數 | 耗時 |
|----------|--------|------|
| 依資源搜尋 | 70 | 0.018s |
| 依狀態搜尋 | 70 | 0.016s |
| 依日期範圍 | 50 | 0.017s |
| 組合篩選 | 50 | 0.016s |

### 5.5 Portal 負載模擬
- Portal 登入: HTTP 200 ✓
- 20 次快速請求: 平均 0.035s, 最大 0.065s ✓
- 所有回應一致 (全部 200) ✓

---

## Phase 6: 安全性測試 — 23/24 (1 FAIL)

### 6.1 SQL Injection (4/4 PASS)
- 資源名稱注入 (`'; DROP TABLE...`) → 安全儲存 ✓
- 搜尋 domain 注入 → ORM 安全處理 ✓
- 預約備註注入 (`' OR 1=1; --`) → 安全儲存 ✓
- 資料表完整性確認 → 全部正常 ✓

### 6.2 XSS Injection (2/2 PASS)
- Html description 欄位 (`<script>alert(1)</script>`) → **已消毒**（script 標籤被移除）✓
- 預約 note 欄位 (`<img onerror=alert(1)>`) → 安全儲存/消毒 ✓

### 6.3 Portal 越權嘗試 (5/5 PASS)
- 修改 admin 使用者記錄 → 阻擋 (AccessError) ✓
- 讀取系統參數 → 阻擋 ✓
- 安裝模組 → 阻擋 ✓
- 刪除/建立資源類型 → 阻擋 (需 Booking/Manager) ✓

### 6.4 跨使用者資料存取 (2/3, 1 FAIL) ⚠️

| 測試 | 結果 | 說明 |
|------|------|------|
| 6.4a: Portal1 建立預約 | PASS | id=103 |
| **6.4b: Portal2 修改 Portal1 的預約** | **FAIL** | **修改成功 — 跨使用者修改未阻擋** |
| 6.4c: Portal2 取消 Portal1 的預約 | PASS | action_cancel 被阻擋 |

### 6.5 Portal HTTP 安全 (4/4 PASS)
- 未登入存取 /my/bookings → 重導至登入頁 (303) ✓
- 存取不存在的預約 → HTTP 400 ✓
- POST 無效 resource_id → HTTP 400 ✓
- POST 無 CSRF token → HTTP 400 ✓

### 6.6 未授權 URL 存取 (6/6 PASS)
- Portal 使用者存取後台路由 → 重導至 /my ✓
- Portal 使用者 call_kw 受限模型 → Server Error ✓

---

## Phase 7: UI/UX 與多語系 — 28/30 (2 FAIL)

### 7.1 後台頁面載入 (3/3 PASS)
- Admin 登入 → 重導至 /odoo ✓
- 後台首頁 → HTTP 200 ✓
- 預約功能 action → 可存取 ✓

### 7.2 Portal 頁面載入 (6/6 PASS)
| 頁面 | 狀態 | 回應時間 |
|------|------|---------|
| /my | 200 | 0.036s |
| /my/booking/resources | 200 | 0.023s |
| /my/booking/resources/2 | 200 | 0.084s |
| /my/bookings | 200 | 0.118s |

### 7.3 繁體中文 (zh_TW) 驗證 (3/3 PASS)
- 資源頁面含中文文字 (21 個中文詞): 跳至內容、我的帳戶、登出、首頁 ✓
- 日期時間格式正確 ✓
- Portal 首頁含中文 (20 個詞): 聯絡人、連線及保安、配置您的連線參數 ✓

### 7.4 錯誤頁面 (5/5 PASS)
- 不存在的資源 (/my/booking/resources/99999) → HTTP 400, 無 traceback ✓
- 不存在的預約 (/my/bookings/99999) → HTTP 400, 無 traceback ✓

### 7.5 響應式設計 (6/6 PASS)
- 所有頁面用手機 User-Agent 回傳 HTTP 200 ✓
- 包含 viewport meta tag ✓

### 7.6 CSS/JS 資源載入 (3/3 PASS)
- CSS bundle 載入成功 ✓
- 預期的 CSS classes 存在 (card, btn-primary, badge, fa-calendar, slot-btn) ✓
- JS bundle 載入成功 ✓

### 7.7 表單驗證 (2/4, 2 FAIL) ⚠️

| 測試 | 結果 | 說明 |
|------|------|------|
| 7.7a: POST 缺少欄位 | PASS | 重導至 error=missing_fields |
| **7.7b: POST resource_id=99999** | **FAIL** | **HTTP 500 (應為 400)** |
| 7.7c: POST resource_id=0 | PASS | 視為缺少欄位 |
| **7.7d: 綜合驗證** | **FAIL** | 因 7.7b 失敗 |

---

## 發現的缺陷

### BUG-001: Portal 使用者跨帳號資料存取 (HIGH) 🔴

**嚴重度**: HIGH — 商用前必須修復
**影響**: Portal 使用者可透過 XML-RPC API 讀取及修改其他 Portal 使用者的預約記錄
**相關測試**: D3a, D3b (Phase 3), 6.4b (Phase 6)

**根因分析**:
- `ir.model.access.csv` 授予 Portal 群組對 `booking.reservation` 的 `read` 和 `write` 權限
- 但**沒有** `ir.rule`（記錄規則）限制 Portal 使用者只能存取自己的記錄
- HTTP Portal controller (`controllers/portal.py`) 有做 partner_id 檢查，但 ORM 層級沒有防護

**修復建議**:
在 `security/` 目錄新增 `ir.rule`：

```xml
<record id="booking_reservation_portal_rule" model="ir.rule">
    <field name="name">Portal users: own reservations only</field>
    <field name="model_id" ref="model_booking_reservation"/>
    <field name="domain_force">[('partner_id', '=', user.partner_id.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_portal'))]"/>
</record>
```

---

### BUG-002: Portal POST 無效 resource_id 回傳 500 (MEDIUM) 🟡

**嚴重度**: MEDIUM — 建議上線前修復
**影響**: 使用者（或攻擊者）送出不存在的 resource_id 時，伺服器回傳 500 Internal Server Error
**相關測試**: 7.7b, 7.7d (Phase 7)

**根因分析**:
- `controllers/portal.py` 的 `portal_create_booking` 方法使用 `browse(resource_id)` 取得資源
- `browse()` 在 ID 不存在時不會立即報錯，但後續操作（如 `_check_resource_access`）會存取不存在記錄的屬性，導致未捕獲的異常

**修復建議**:
在 controller 中新增存在性檢查：

```python
resource = request.env['booking.resource.type'].sudo().browse(resource_id)
if not resource.exists():
    return request.redirect('/my/bookings/new?error=invalid_resource')
```

---

### BUG-003: XML 檢視定義順序錯誤 (已修復) ✅

**嚴重度**: HIGH (安裝時阻塞)
**狀態**: 已在部署時修復
**影響**: 模組無法安裝，因為 Calendar View 引用了尚未定義的 Form View

**根因**: `booking_reservation_views.xml` 中 Calendar View 使用 `quick_create_view_id="%(view_booking_reservation_form)d"` 引用 Form View，但 Form View 在 Calendar View 之後才定義。

**已實施的修復**: 將 Form View 的 `<record>` 移至 Calendar View 之前。

---

## 設計觀察（非缺陷）

這些行為是設計決策，非缺陷，但值得注意：

| 項目 | 行為 | 影響 |
|------|------|------|
| `advance_days` | 僅在 Portal 端驗證，後台不受限 | 管理員可預約任何天數內的時段 |
| 可用時間視窗 | 僅作為 Portal 時段產生的篩選，後台不受限 | 管理員可在非營業時間預約 |
| 已停用資源 | 後台仍可對其建立預約 | 管理員 override 行為 |
| 非標準時段長度 | 後台允許預約不符合 slot_duration 的長度 | 例如在 1h 時段資源上預約 45min |
| XSS in Html field | `<script>` 標籤被 Odoo sanitizer 移除 | 安全，但 `<img>` 標籤保留 |

---

## 效能基準

| 操作 | 結果 |
|------|------|
| 建立 100 個資源 | 3.27s (32.7ms/個) |
| 建立 50 個預約 | 2.03s (40.6ms/個) |
| 建立+取消 20 個預約 | 2.21s (110.5ms/對) |
| 搜尋 70 筆記錄 | 16-18ms |
| Portal 頁面回應 | 23-118ms |
| 20 次 Portal 連續請求 | avg 35ms, max 65ms |

---

## 測試檔案清單

| 檔案 | 說明 |
|------|------|
| `tests/odoo_rpc.py` | XML-RPC 客戶端函式庫 |
| `tests/test_config.json` | 測試環境設定 (使用者/資源/群組 ID) |
| `tests/phase0_setup.py` | Phase 0: 環境設定 |
| `tests/test_install_and_setup.py` | 模組安裝與設定 |
| `tests/phase1_2_backend_tests.py` | Phase 1-2: 後台 CRUD 與權限測試 |
| `tests/phase3_portal_tests.py` | Phase 3: Portal 使用者測試 |
| `tests/phase4_edge_cases.py` | Phase 4: 邊緣事件與衝突偵測 |
| `tests/phase5_6_stress_security.py` | Phase 5-6: 壓力與安全性測試 |
| `tests/phase7_ui_ux.py` | Phase 7: UI/UX 與多語系測試 |

---

## 上線前建議

### 必須修復 (Must Fix)
1. **BUG-001**: 新增 `ir.rule` 限制 Portal 使用者只能存取自己的預約記錄
2. **BUG-003**: 修正 GitHub 原始碼中 XML 檢視的定義順序

### 建議修復 (Should Fix)
3. **BUG-002**: 在 Portal controller 中新增 resource 存在性檢查，避免 500 錯誤

### 建議改善 (Nice to Have)
4. 考慮在後台也驗證 `advance_days` 限制（目前僅 Portal 端驗證）
5. 可用時間欄位的 help text 可更清楚說明僅影響 Portal 端
6. `<img>` 標籤未被 sanitizer 移除，考慮在 note 欄位使用 Char 而非 Text

---

*報告產生時間: 2026-03-20 12:30 GMT+8*
*測試執行者: Automated Test Suite (XML-RPC + HTTP)*
