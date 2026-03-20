# Odoo 18 預約系統瀏覽器完整功能測試報告

**測試日期：** 2026-03-20
**測試工具：** Playwright (Chromium headless)
**測試實例：** http://localhost:9071
**模組版本：** odoo_booking_reservation (Odoo 18)

---

## 測試總覽

| 階段 | 說明 | 測試數 | 通過 | 通過率 |
|------|------|--------|------|--------|
| **A. Portal 前台** | Portal 使用者完整流程 | 62 | 62 | **100%** |
| **B. Admin 後台** | Admin 管理功能 | 30 | 30 | **100%** |
| **合計** | | **92** | **92** | **100%** |

---

## A. Portal 前台測試 (62/62 通過)

### A1. 登入流程 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A1.1 | 登入頁面載入 | PASS | 登入表單正常顯示 |
| A1.2 | 錯誤密碼被拒絕 | PASS | 停留在登入頁，顯示錯誤訊息 |
| A1.3 | portal1 登入成功 | PASS | 重導至 /my |
| A1.4 | portal3 登入成功 | PASS | 重導至 /my |

**截圖：** `A1-login-page.png`, `A1-portal1-home.png`

---

### A2. Portal 首頁 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A2.1 | 首頁包含預約連結 | PASS | My Bookings 連結可見 |
| A2.2 | 首頁包含資源連結 | PASS | Resources 連結可見 |
| A2.3 | 導航列有登出連結 | PASS | |

**截圖：** `A2-portal-home.png`

---

### A3. 資源列表頁 (5/5)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A3.1 | 資源列表頁載入 | PASS | HTTP 200 OK |
| A3.2 | 公開資源全部可見 | PASS | Conference Room A, Small Meeting Room B, Projector, Phone Booth 均可見 |
| A3.3 | portal1 可見 VIP Room C | PASS | 具存取權限的 portal1 可看到 |
| A3.4 | portal3 不可見 VIP Room C | PASS | 無權限的 portal3 看不到 |
| A3.5 | 資源卡片有詳情連結 | PASS | 共 5 個詳情連結 |

**截圖：** `A3-resource-list.png`

**存取控制驗證：** VIP Room C 設定為「Specific Contacts」，只有被授權的 portal1/portal2 可看到，portal3 被正確排除。

---

### A4. 資源詳情頁 (8/8)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A4.1 | Conference Room A 詳情頁載入 | PASS | |
| A4.2 | 資源資訊卡片包含完整資訊 | PASS | Location, Capacity, Duration 均有 |
| A4.3 | 時段按鈕連結到確認頁 | PASS | 54 個確認頁連結 (非直接建立) |
| A4.4 | 無舊式直接建立表單 | PASS | 舊表單數=0 (已全部改為連結) |
| A4.5 | 日期導航功能存在 | PASS | 前/後日期導航連結 |
| A4.6 | 已預約時段有視覺標示 | PASS | 已被佔用的時段有明確標示 |
| A4.7 | portal3 不可存取 VIP Room C | PASS | 被重導至資源列表 |
| A4.8 | 不存在資源友善處理 (非500) | PASS | 存取 resource/99999 不會 500 錯誤 |

**截圖：** `A4-resource-detail.png`, `A4-portal3-vip-blocked.png`

**關鍵改動驗證：** 時段按鈕已從舊式 `<form>` POST 改為 `<a>` GET 連結，指向新的確認頁面 `/my/bookings/confirm`。

---

### A5. 確認頁面 (新功能) (11/11)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A5.1 | 確認頁面載入 | PASS | URL: `/my/bookings/confirm?resource_id=5&...` |
| A5.2 | 顯示資源名稱 | PASS | Projector |
| A5.3 | 顯示日期時間 | PASS | Friday, March 20, 2026 / 09:00 - 10:00 |
| A5.4 | 顯示時長 | PASS | 1.0 hour(s) |
| A5.5 | 顯示地點 | PASS | IT Department |
| A5.6 | 備註輸入欄存在 | PASS | textarea 可輸入 |
| A5.7 | 確認預約按鈕存在 | PASS | Confirm Booking 按鈕 |
| A5.8 | 返回按鈕存在 | PASS | Back 按鈕連回資源詳情頁 |
| A5.9 | CSRF 保護存在 | PASS | csrf_token hidden field |
| A5.10 | 表單指向 /my/bookings/create | PASS | POST 至建立端點 |
| A5.11 | 資源資訊側邊欄存在 | PASS | Resource Info 卡片 |

**截圖：** `A5-confirm-page.png`

**新功能說明：** 此為本次新增的確認頁面，在使用者選擇時段後、正式建立預約前，顯示完整的預約摘要（資源名稱、日期時間、時長、地點、容量）及可選的備註欄。

---

### A6. 建立預約 (5/5)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A6.1 | 預約建立成功 | PASS | booking_id=289，重導至預約詳情頁 |
| A6.2 | 備註成功儲存 | PASS | 自訂備註正確儲存 |
| A6.3 | 成功訊息顯示 | PASS | 建立成功提示訊息 |
| A6.4 | 第二筆預約建立 (供取消測試) | PASS | booking_id=290 |
| A6.5 | 返回按鈕回到資源詳情頁 | PASS | Back 按鈕正常運作 |

**截圖：** `A6-confirm-with-note.png`, `A6-booking-created.png`

---

### A7. 預約列表 (7/7)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A7.1 | 預約列表頁載入 | PASS | |
| A7.2 | 列表包含預約記錄 | PASS | 8 筆記錄 |
| A7.3 | 狀態徽章顯示 | PASS | Confirmed / Cancelled 徽章 |
| A7.4 | 篩選功能存在 | PASS | |
| A7.5 | 依狀態篩選 (confirmed) | PASS | filterby=confirmed 正常 |
| A7.6 | 依日期排序 | PASS | sortby=date 正常 |
| A7.7 | portal2 不可見 portal1 的預約 | PASS | 跨使用者隱私保護 |

**截圖：** `A7-booking-list.png`

---

### A8. 預約詳情 (8/8)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A8.1 | 預約詳情頁載入 | PASS | |
| A8.2 | 顯示資源名稱 | PASS | |
| A8.3 | 顯示日期時間 | PASS | |
| A8.4 | 顯示時長 | PASS | |
| A8.5 | 顯示備註 | PASS | |
| A8.6 | 顯示狀態 (Confirmed) | PASS | |
| A8.7 | 取消按鈕存在 | PASS | |
| A8.8 | portal2 不能查看 portal1 的預約 | PASS | 跨使用者存取被阻擋 |

**截圖：** `A8-booking-detail.png`

---

### A9. 取消預約 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A9.1 | 取消按鈕可見 | PASS | |
| A9.2 | 預約取消成功 | PASS | 狀態變更為 Cancelled |
| A9.3 | portal2 不能取消 portal1 的預約 | PASS | POST 方法限制 + ir.rule 保護 |

**截圖：** `A9-booking-cancelled.png`

---

### A10. 存取控制 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A10.1 | 未登入存取資源列表→重導登入 | PASS | 重導至 /web/login |
| A10.2 | 未登入存取預約列表→重導登入 | PASS | |
| A10.3 | 未登入存取新建預約→重導登入 | PASS | |
| A10.4 | portal3 構造URL存取VIP確認頁被拒 | PASS | 重導至 ?error=unauthorized |

**說明：** 所有 Portal 頁面均正確要求 `auth='user'`，未登入使用者自動重導至登入頁。portal3 嘗試透過手動構造 URL 存取 VIP Room C 的確認頁面時，伺服器端 `_check_resource_access()` 正確阻擋並重導。

---

### A11. 響應式設計 - 手機 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| A11.1 | 資源列表頁 (手機) | PASS | viewport=375x812 |
| A11.2 | 資源詳情頁 (手機) | PASS | 時段按鈕正常顯示 |
| A11.3 | 確認頁面 (手機) | PASS | |
| A11.4 | 預約列表頁 (手機) | PASS | |

**截圖：** `A11-mobile-resources.png`, `A11-mobile-resource-detail.png`, `A11-mobile-confirm.png`, `A11-mobile-bookings.png`

---

## B. Admin 後台測試 (30/30 通過)

### B1. Admin 登入 (1/1)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| B1.1 | Admin 登入成功 | PASS | 重導至 /odoo/discuss |

**截圖：** `B1-admin-login.png`

---

### B2. 資源分類管理 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| B2.1 | 資源分類管理頁面載入 | PASS | /odoo/action-176 |
| B2.2 | 分類記錄顯示 | PASS | 2 筆分類記錄 |
| B2.3 | 分類表單頁面載入 | PASS | 點擊記錄可開啟表單 |

**截圖：** `B2-categories.png`, `B2-category-form.png`

---

### B3. 資源類型管理 (5/5)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| B3.1 | 資源類型列表顯示 | PASS | /odoo/action-177 |
| B3.2 | 現有資源記錄可見 | PASS | 5 筆資源記錄 |
| B3.3 | 資源表單頁面載入 | PASS | 點擊記錄可開啟表單 |
| B3.4 | 表單包含容量/地點欄位 | PASS | Capacity=true, Location=true |
| B3.5 | 資源表單包含可用時段設定 | PASS | Availability 設定區塊存在 |

**截圖：** `B3-resources-list.png`, `B3-resource-form.png`

**資源列表內容：**
- Conference Room A (Building 1, Floor 3, 容量 20, All Portal Users)
- Small Meeting Room B (Building 1, Floor 2, 容量 6, All Portal Users)
- VIP Room C (Building 2, Floor 5, 容量 10, Specific Contacts)
- Projector (IT Department, 容量 1, All Portal Users)
- Phone Booth (Building 1, Floor 1, 容量 1, All Portal Users)

---

### B4. 預約管理 - 日曆檢視 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| B4.1 | 預約日曆檢視載入 | PASS | /odoo/action-178 |
| B4.2 | 檢視切換按鈕存在 | PASS | 2 個按鈕 (列表/日曆) |
| B4.3 | 切換列表檢視成功 | PASS | |

**截圖：** `B4-reservations-calendar.png`, `B4-reservations-list.png`

---

### B5. 預約管理 - 列表檢視 (7/7)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| B5.1 | 所有預約列表載入 | PASS | /odoo/action-179 |
| B5.2 | 預約記錄數量 | PASS | 46 筆記錄 |
| B5.3 | 搜尋欄存在 | PASS | |
| B5.4 | 預約表單頁面載入 | PASS | 點擊記錄可開啟表單 |
| B5.5 | 表單顯示狀態欄位 | PASS | Confirmed / Cancelled |
| B5.6 | 表單顯示預約者資訊 | PASS | Partner / Portal User |
| B5.7 | 表單顯示資源資訊 | PASS | Resource 欄位 |

**截圖：** `B5-all-reservations.png`, `B5-reservation-form.png`

**預約列表驗證：** Admin 可看到所有使用者的預約記錄，包含 Portal User 1、Portal User 2、Portal User 3 的預約，以及多種資源（Conference Room A、VIP Room C 等）。列表顯示欄位包含：Name、Resource、Start、End、Duration、Booked By、Status。

---

### B6. Admin 後台操作 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| B6.1 | Admin 可看到所有使用者的預約 | PASS | portal1 和 portal2 的記錄均可見 |
| B6.2 | 新增預約表單載入 | PASS | /odoo/action-179/new |
| B6.3 | 捨棄新表單成功 | PASS | |
| B6.4 | 新增資源表單載入 | PASS | /odoo/action-177/new |

**截圖：** `B6-new-reservation-form.png`, `B6-new-resource-form.png`

---

### B7. Admin 選單導航 (4/4)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| B7.1 | 日曆應用載入 | PASS | /odoo/calendar |
| B7.2 | 預約相關選單項目可見 | PASS | 選單: 日曆 / Resource Bookings / 配置 |
| B7.3 | 點選「Resource Bookings」選單成功 | PASS | 導向日曆檢視 |
| B7.4 | 配置子選單包含預約資源/分類 | PASS | |

**截圖：** `B7-calendar-app.png`, `B7-booking-menu-click.png`, `B7-admin-menu.png`

**選單結構驗證：**
```
日曆 (Calendar App)
├── 日曆 (Calendar - 原有)
├── Resource Bookings (預約日曆 - 模組新增)
└── 配置 (Configuration)
    ├── Booking Resources (預約資源)
    └── Resource Categories (資源分類)
```

---

### B8. Admin 平板畫面 (3/3)

| # | 測試項目 | 結果 | 說明 |
|---|---------|------|------|
| B8.1 | 預約管理頁面 (平板) | PASS | viewport=768x1024 |
| B8.2 | 資源管理頁面 (平板) | PASS | viewport=768x1024 |
| B8.3 | 分類管理頁面 (平板) | PASS | viewport=768x1024 |

**截圖：** `B8-tablet-reservations.png`, `B8-tablet-resources.png`, `B8-tablet-categories.png`

---

## 測試帳號

| 帳號 | 密碼 | 角色 | 說明 |
|------|------|------|------|
| admin | admin | 管理員 | 後台完整管理權限 |
| portal1 | portal1 | Portal 使用者 | 可存取所有資源 (含 VIP) |
| portal2 | portal2 | Portal 使用者 | 可存取所有資源 (含 VIP) |
| portal3 | portal3 | Portal 使用者 (受限) | 只能存取公開資源，不可存取 VIP |

---

## 截圖清單 (34 張)

### Portal 截圖 (16 張)
| 檔名 | 說明 |
|------|------|
| A1-login-page.png | 登入頁面 |
| A1-portal1-home.png | portal1 首頁 |
| A2-portal-home.png | Portal 首頁導航 |
| A3-resource-list.png | 資源列表頁 |
| A4-resource-detail.png | 資源詳情頁 (含時段) |
| A4-portal3-vip-blocked.png | portal3 被阻擋存取 VIP |
| A5-confirm-page.png | **確認頁面 (新功能)** |
| A6-confirm-with-note.png | 確認頁含備註 |
| A6-booking-created.png | 預約建立成功 |
| A7-booking-list.png | 預約列表 |
| A8-booking-detail.png | 預約詳情 |
| A9-booking-cancelled.png | 預約已取消 |
| A11-mobile-resources.png | 手機版資源列表 |
| A11-mobile-resource-detail.png | 手機版資源詳情 |
| A11-mobile-confirm.png | 手機版確認頁 |
| A11-mobile-bookings.png | 手機版預約列表 |

### Admin 截圖 (18 張)
| 檔名 | 說明 |
|------|------|
| B1-admin-login.png | Admin 登入後首頁 |
| B2-categories.png | 資源分類列表 |
| B2-category-form.png | 分類表單 |
| B3-resources-list.png | 資源類型列表 (5 筆) |
| B3-resource-form.png | 資源表單 (含可用時段) |
| B4-reservations-calendar.png | 預約日曆檢視 |
| B4-reservations-list.png | 預約列表檢視 (從日曆切換) |
| B5-all-reservations.png | 所有預約列表 (46 筆) |
| B5-reservation-form.png | 預約表單詳情 |
| B6-new-reservation-form.png | 新增預約表單 |
| B6-new-resource-form.png | 新增資源表單 |
| B7-calendar-app.png | 日曆應用首頁 |
| B7-booking-menu-click.png | 點選 Resource Bookings 選單 |
| B7-admin-menu.png | Admin 選單結構 |
| B8-tablet-reservations.png | 平板版預約列表 |
| B8-tablet-resources.png | 平板版資源列表 |
| B8-tablet-categories.png | 平板版分類列表 |

---

## 新功能：預約確認頁面

### 流程變更

```
舊流程: 資源詳情頁 → 點擊時段 → 直接建立預約 → 預約詳情頁
新流程: 資源詳情頁 → 點擊時段 → 確認頁面 → 確認建立 → 預約詳情頁
```

### 確認頁面功能

1. **Booking Summary 卡片**
   - 資源名稱
   - 日期與時間 (格式: Friday, March 20, 2026 / 09:00 - 10:00)
   - 時長 (小時)
   - 地點 (如有)
   - 容量 (如有)
   - Note 備註欄 (可選)

2. **操作按鈕**
   - Back: 返回資源詳情頁
   - Confirm Booking: POST 建立預約

3. **Resource Info 側邊欄**
   - 資源名稱與描述
   - View Available Slots 連結

4. **安全機制**
   - CSRF Token 保護
   - 伺服器端參數驗證
   - 資源存取權限檢查

### 修改的檔案

| 檔案 | 修改內容 |
|------|---------|
| `controllers/portal.py` | 新增 `portal_confirm_booking` GET 路由 |
| `views/portal_templates.xml` | 時段按鈕改為 `<a>` 連結 + 新增確認頁模板 |

---

## 結論

**92/92 測試全部通過 (100%)**

所有 Portal 前台和 Admin 後台功能均正常運作，包括：
- 登入/登出流程
- 資源瀏覽與存取控制
- 新增的確認頁面流程
- 預約建立、查看、取消
- 跨使用者隱私保護
- Admin 後台 CRUD 操作
- 選單導航與檢視切換
- 響應式設計 (手機/平板)
