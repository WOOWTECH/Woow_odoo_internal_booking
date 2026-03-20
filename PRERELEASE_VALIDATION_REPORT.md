# WOOWTECH Odoo 18 預約系統 — 正式預發佈驗證報告

**模組名稱**: `odoo_booking_reservation`
**驗證日期**: 2026-03-20
**驗證環境**: Odoo 18 (Podman container) @ localhost:9071
**測試工具**: Playwright (Headless Chromium)
**測試結果**: **72/72 全部通過 (100%)**

---

## 一、驗證總覽

本次驗證比照世界頂級軟體公司（Google、Stripe、Microsoft）的預發佈標準，以五大面向進行全面自動化驗證：

| 階段 | 面向 | 測試數 | 通過 | 結果 |
|------|------|--------|------|------|
| P1 | 安全性測試 (Security) | 19 | 19 | **PASS** |
| P2 | 資料完整性 (Data Integrity) | 7 | 7 | **PASS** |
| P3 | 邊界值與極端情況 (Boundary) | 14 | 14 | **PASS** |
| P4 | 商業邏輯驗證 (Business Logic) | 18 | 18 | **PASS** |
| P5 | 管理後台完整性 (Admin Backend) | 14 | 14 | **PASS** |
| **合計** | | **72** | **72** | **100%** |

### 測試帳戶

| 帳戶 | 角色 | 用途 |
|------|------|------|
| `admin` | 系統管理員 | 後台管理功能驗證 |
| `portal1` | Portal 使用者 (VIP) | 有 VIP Room 存取權限 |
| `portal2` | Portal 使用者 | 跨使用者安全測試 |
| `portal3` | Portal 使用者 (無 VIP) | 權限隔離驗證 |

---

## 二、P1 安全性測試 (19/19 PASS)

### S1: XSS 跨站腳本注入 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 1 | Note 欄位 XSS 注入被阻擋 | PASS | `<script>alert("XSS")</script>` payload 未被作為 HTML 執行 |
| 2 | URL 參數 XSS 注入被阻擋 | PASS | script 標籤在 URL 參數中被轉義或重導 |

### S2: CSRF 跨站請求偽造防護 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 3 | POST 無 CSRF Token 被拒絕 | PASS | HTTP 400 |
| 4 | POST 偽造 CSRF Token 被拒絕 | PASS | HTTP 400 |

### S3: 參數篡改 (5/5)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 5 | portal3 篡改 resource_id 存取 VIP 被拒 | PASS | 重導至 `?error=unauthorized` |
| 6 | 負數 resource_id 被安全處理 | PASS | 重導至 `?error=invalid_resource` |
| 7 | 非數字 resource_id 被安全處理 | PASS | 重導至 `?error=invalid_resource` |
| 8 | SQL 注入嘗試被安全處理 | PASS | `1 OR 1=1` → 重導至 `?error=invalid_resource` |
| 9 | 超大 resource_id 被安全處理 | PASS | `99999999999` → 重導至 `?error=invalid_resource` |

### S4: 未授權存取 (5/5)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 10 | 未登入存取確認頁 → 重導登入 | PASS | HTTP 302 → `/web/login` |
| 11 | 未登入存取資源列表 → 重導登入 | PASS | HTTP 302 → `/web/login` |
| 12 | 未登入存取預約列表 → 重導登入 | PASS | HTTP 302 → `/web/login` |
| 13 | portal2 不能查看 portal1 的預約詳情 | PASS | MissingError 阻擋跨使用者存取 |
| 14 | portal2 不能取消 portal1 的預約 | PASS | HTTP 400 拒絕跨使用者操作 |

### S5: 日期時間篡改 (5/5)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 15 | 過去日期確認頁被重導 | PASS | 重導至 `?error=past_slot` |
| 16 | 格式錯誤的日期時間被安全處理 | PASS | 重導至 `?error=invalid_datetime` |
| 17 | 結束時間早於開始時間的處理 | PASS | 確認頁可載入，建立時被 CHECK constraint 阻擋 |
| 18 | 缺少日期參數被安全處理 | PASS | 重導至 `?error=missing_fields` |
| 19 | 空白參數被安全處理 | PASS | 重導至 `?error=missing_fields` |

---

## 三、P2 資料完整性測試 (7/7 PASS)

### D1: 重複提交防護 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 20 | 第一次提交成功 | PASS | 建立預約並重導至詳情頁 |
| 21 | 重複提交同一時段被阻擋 (overlap) | PASS | `_check_no_overlap` 阻擋，顯示 overlap 錯誤 |

### D2: 跨使用者同時段預約 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 22 | portal1 預約成功 | PASS | 成功建立預約 |
| 23 | portal2 預約同一時段被阻擋 | PASS | overlap constraint 阻擋不同使用者搶同一時段 |

### D3: 取消後重新預約 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 24 | 預約取消成功 | PASS | 狀態切換至 cancelled，顯示 `success=cancelled` |
| 25 | 已取消時段應可重新預約 | PASS | overlap domain 僅檢查 `state=confirmed` |

### D4: 狀態轉換完整性 (1/1)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 26 | 已取消預約不顯示取消按鈕 | PASS | UI 正確隱藏已取消預約的取消按鈕 |

---

## 四、P3 邊界值與極端情況 (14/14 PASS)

### E1: 時段生成邊界 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 27 | 超出 advance_days 的日期被鉗制 | PASS | `?date=2027-06-01` 被鉗制到最大日期 (advance_days=30) |
| 28 | 過去日期被鉗制到今天 | PASS | `?date=2025-01-01` 被鉗制到今天 |
| 29 | 週末時段依可用時段設定生成 | PASS | 週末正常生成 20 個時段 |
| 30 | 無效日期格式不導致 500 錯誤 | PASS | `?date=not-a-date` 安全降級為今天 |

### E2: 分頁與大量資料 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 31 | 預約列表分頁功能存在 | PASS | 分頁器正確顯示 |
| 32 | 頁碼 0 不導致錯誤 | PASS | 安全處理無效頁碼 |
| 33 | 超大頁碼不導致錯誤 | PASS | `page=9999` 不引發 500 錯誤 |

### E3: 不存在的資源 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 34 | 不存在的資源不顯示 500 錯誤 | PASS | AccessError 正確處理 |
| 35 | 不存在的預約不顯示 500 錯誤 | PASS | MissingError 正確處理 |
| 36 | 不存在的預約取消被安全處理 | PASS | HTTP 400 |

### E4: 資源列表 (1/1)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 37 | 資源列表正常載入 | PASS | 顯示 5 個可用資源 |

### E5: 超長文字輸入 (1/1)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 38 | 5000 字元備註不導致錯誤 | PASS | 成功建立包含超長備註的預約 |

### E6: Unicode 與特殊字元 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 39 | Unicode/Emoji/特殊字元備註正常儲存 | PASS | 中文、日文、韓文、阿拉伯文、Emoji 均正常 |
| 40 | Unicode 備註正確顯示在詳情頁 | PASS | 多語言文字正確渲染 |

---

## 五、P4 商業邏輯驗證 (18/18 PASS)

### L1: 時段顯示與預約狀態一致性 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 41 | 可用時段以綠色連結顯示 | PASS | 54 個可預約時段 |
| 42 | 已佔用/已預約時段有區分顯示 | PASS | 自己預約=3, 他人佔用=1 |

### L2: 篩選與排序準確性 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 43 | 篩選「已確認」不顯示已取消記錄 | PASS | domain 過濾正確 |
| 44 | 篩選「已取消」結果正確 | PASS | 僅顯示 cancelled 記錄 |
| 45 | 依資源排序功能正常 | PASS | order 欄位正確套用 |

### L3: 預約詳情完整性 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 46 | 詳情頁顯示資源名稱 | PASS | |
| 47 | 詳情頁顯示日期時間 | PASS | |
| 48 | 詳情頁顯示時長 | PASS | |
| 49 | 詳情頁顯示狀態 | PASS | |

### L4: 資源存取控制全面驗證 (5/5)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 50 | portal1 (VIP 權限) 可見 VIP Room | PASS | share_type=specific 權限正確 |
| 51 | portal1 可見所有授權資源 | PASS | 5 個資源全部可見 |
| 52 | portal3 (無 VIP 權限) 不可見 VIP Room | PASS | 資源列表正確過濾 |
| 53 | portal3 只能見到公開資源 | PASS | 4 個公開資源可見 |
| 54 | portal3 直接 URL 存取 VIP 被拒 | PASS | HTTP 403 AccessError |

### L5: 確認頁面資訊準確性 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 55 | 確認頁顯示資源名稱 | PASS | resource_id=2 名稱正確 |
| 56 | 隱藏欄位 resource_id 與 URL 一致 | PASS | hidden=2, url=2 |
| 57 | 隱藏欄位 start_datetime 與 URL 一致 | PASS | 完全匹配 |
| 58 | 隱藏欄位 end_datetime 與 URL 一致 | PASS | 完全匹配 |

---

## 六、P5 管理後台完整性 (14/14 PASS)

### A1: Admin 狀態管理 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 59 | Admin 可查看所有預約記錄 | PASS | 72 筆記錄可見 |
| 60 | 表單包含狀態管理按鈕 | PASS | 確認/取消按鈕均存在 |
| 61 | 表單包含 Chatter (追蹤記錄) | PASS | mail.thread 正確整合 |

### A2: Admin 資源管理完整性 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 62 | 資源表單有多分頁結構 | PASS | Notebook 分頁正確渲染 |
| 63 | 資源表單有預約數智慧按鈕 | PASS | oe_stat_button 正確顯示 |
| 64 | 資源表單有存取控制設定 | PASS | share_type/allowed_partner 在分頁中 (4 個分頁) |
| 65 | 資源表單有可用時段設定 | PASS | availability_ids inline 編輯 |

### A3: Admin 分類與動態屬性 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 66 | 分類表單有屬性定義區塊 | PASS | properties_definition 欄位存在 |
| 67 | 分類表單顯示關聯資源 | PASS | 資源列表正確顯示 |

### A4: Admin 日曆檢視 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 68 | 日曆檢視正確渲染 | PASS | o_calendar 元件正確載入 |
| 69 | 日曆有篩選面板 | PASS | filter 面板存在 |
| 70 | 日曆有日/週/月切換 | PASS | 切換功能正常 |

### A5: Admin 搜尋與群組 (2/2)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| 71 | 列表有搜尋欄 | PASS | o_searchview 正確顯示 |
| 72 | 搜尋下拉選單功能正常 | PASS | dropdown 正常運作 |

---

## 七、驗證期間發現並修復的缺陷

### BUG-001: Portal 資源詳情頁日期驗證缺失 (已修復)

- **嚴重程度**: 中
- **發現方式**: E1 邊界值測試
- **問題描述**: `portal_resource_detail` 控制器未對 URL 中的 `date` 參數進行邊界驗證。使用者可透過手動修改 URL 查看過去日期或超出 `advance_days` 的遠未來日期時段。
- **影響**: 使用者可能嘗試預約過期時段，雖然 `portal_create_booking` 不一定會阻擋，但 UI 層面不應顯示這些時段。
- **修復方案**: 三層縱深防禦
  1. **資源詳情頁 (GET)**: 加入日期鉗制邏輯，`selected_date` 不得早於今天或超過 `max_date`
  2. **確認頁 (GET)**: 加入過去日期和超出 advance_days 的驗證，不符合時重導並帶 `?error=past_slot` / `?error=too_far_ahead`
  3. **建立端點 (POST)**: 縱深防禦，在實際建立前再次驗證日期
- **修復檔案**:
  - `controllers/portal.py`: `portal_resource_detail()`, `portal_confirm_booking()`, `portal_create_booking()`
  - `views/portal_templates.xml`: 導航箭頭以 `show_prev` / `show_next` 控制是否可點擊

---

## 八、安全性評估摘要

| 攻擊向量 | 防護狀態 | 機制 |
|----------|----------|------|
| XSS (跨站腳本) | 已防護 | QWeb 模板自動轉義 |
| CSRF (跨站請求偽造) | 已防護 | Odoo 內建 CSRF Token 驗證 |
| SQL Injection | 已防護 | ORM 參數化查詢、int() 型別轉換 |
| Parameter Tampering | 已防護 | 伺服器端參數驗證與型別檢查 |
| Unauthorized Access | 已防護 | `auth='user'`、`partner_id` 比對、`_check_partner_access()` |
| 跨使用者資料存取 | 已防護 | Record-level security rules + 控制器檢查 |
| 日期時間篡改 | 已防護 | 三層縱深防禦（顯示層、確認層、建立層） |

---

## 九、測試截圖清單

所有截圖保存於 `/tmp/prerelease-screenshots/`:

| 檔案 | 說明 |
|------|------|
| `S1-xss-note.png` | XSS 注入 Note 欄位測試 |
| `S1-xss-url.png` | XSS 注入 URL 參數測試 |
| `S3-parameter-tamper-vip.png` | VIP 資源參數篡改測試 |
| `S3-sql-injection.png` | SQL 注入嘗試測試 |
| `S4-cross-user-view.png` | 跨使用者查看預約測試 |
| `S5-past-datetime.png` | 過去日期確認頁測試 |
| `S5-end-before-start.png` | 結束早於開始時間測試 |
| `D1-first-submit.png` | 第一次成功提交 |
| `D1-double-submit.png` | 重複提交測試 |
| `D2-cross-user-overlap.png` | 跨使用者同時段測試 |
| `D3-cancelled.png` | 預約取消測試 |
| `D4-cancelled-no-cancel-btn.png` | 已取消預約 UI 狀態 |
| `E1-far-future.png` | 遠未來日期鉗制測試 |
| `E1-past-date.png` | 過去日期鉗制測試 |
| `E1-invalid-date.png` | 無效日期格式測試 |
| `E2-pagination.png` | 分頁功能測試 |
| `E3-nonexistent-resource.png` | 不存在資源測試 |
| `E3-nonexistent-booking.png` | 不存在預約測試 |
| `E5-long-note.png` | 5000 字元備註測試 |
| `E6-unicode-note.png` | Unicode/Emoji 備註測試 |
| `L1-slot-status.png` | 時段狀態顯示一致性 |
| `L2-sort-resource.png` | 依資源排序測試 |
| `L3-booking-detail.png` | 預約詳情完整性 |
| `L4-portal3-vip-blocked.png` | VIP 權限隔離測試 |
| `L5-confirm-accuracy.png` | 確認頁資訊準確性 |
| `A1-admin-form.png` | Admin 預約表單 |
| `A2-resource-form-full.png` | Admin 資源表單完整檢視 |
| `A3-category-form.png` | Admin 分類表單 |
| `A4-calendar-view.png` | Admin 日曆檢視 |
| `A5-search-filters.png` | Admin 搜尋篩選功能 |

---

## 十、結論

WOOWTECH Odoo 18 預約系統已通過全部 **72 項預發佈驗證測試**，涵蓋安全性、資料完整性、邊界值、商業邏輯及管理後台五大面向。驗證期間發現的一項日期驗證缺陷已修復並經重新測試確認。

**發佈建議**: 模組已達到商用發佈標準，可進入正式發佈流程。

---

*本報告由自動化測試套件生成，測試腳本: `/tmp/playwright-prerelease-validation.js`*
*測試結果 JSON: `/tmp/prerelease-screenshots/prerelease-results.json`*
