# Findings & Decisions — Odoo Booking Reservation 商用前測試

## Requirements
- 全面性商用前測試：內部/Portal/外部使用者
- 權限驗證、操作流程、邊緣事件、暴力測試
- 測試資料保留供後續參考
- 測試環境：odoo-calendar (port 9071)

## Research Findings

### 模組架構
- 4 個模型：booking.resource.category, booking.resource.type, booking.resource.availability, booking.reservation
- 3 種權限群組：Manager (完整 CRUD), User (有限 CRUD), Portal (唯讀資源 + 建立/修改預約)
- Portal 路由：7 個 HTTP 端點
- 後台檢視：日曆、列表、表單、搜尋
- 依賴：base, mail, calendar, portal

### 安全機制
- ir.model.access.csv：12 條存取規則
- booking_groups.xml：2 個群組定義
- partner_access 檢查：預約時驗證合作夥伴權限
- overlap 檢查：防止雙重預約
- Portal 隱私：HTTP 路由使用者只能看到自己的預約詳情
- **⚠️ 缺少 ir.rule 記錄規則：Portal 使用者可透過 RPC 存取所有預約**

### 安全測試結果
- SQL Injection: **安全** — ORM 正確處理所有注入嘗試
- XSS: **安全** — Odoo sanitizer 移除 `<script>` 標籤，Html 欄位自動消毒
- CSRF: **安全** — 未帶 token 的 POST 被拒絕 (400)
- Privilege Escalation: **安全** — ACL 正確阻擋越權操作
- Cross-User Data: **不安全** — RPC 層級無記錄隔離

### 效能基準
- 100 資源建立: 3.27s
- 50 預約建立: 2.03s
- 搜尋效能: 16-18ms (70+ 筆記錄)
- Portal 頁面回應: 23-118ms
- 20 次連續 HTTP 請求: avg 35ms, max 65ms

## Technical Decisions
| Decision | Rationale |
|----------|-----------|
| 使用 XML-RPC 進行自動化測試 | Odoo 原生 API，可直接操作模型 |
| 使用 requests 進行 Portal 測試 | 模擬真實 HTTP 請求，含 CSRF 處理 |
| 使用 safe_call_action() helper | Odoo action 方法返回 None，XML-RPC 無法 marshal |
| 使用 faultCode=4 判斷 AccessError | 中文環境錯誤訊息為中文，改用 fault code |
| 5 個 agent 平行執行測試 | 加速測試，各 phase 獨立不相依 |

## Issues Encountered
| Issue | Resolution |
|-------|------------|
| XML 檢視定義順序錯誤 | 移動 Form View 到 Calendar View 之前 |
| read() kwargs 傳遞錯誤 | 建立專用 read() 方法正確傳遞 fields |
| action_cancel 返回 None | 建立 safe_call_action() 捕獲 marshal error |
| create() 返回 list | 修正 OdooRPC.create() 取第一個元素 |
| slot_interval=0 constraint | 修正測試資料為正值 |
| Admin 無 Booking 權限 | 程式化加入 Booking Manager 群組 |

## Bugs Discovered

### BUG-001: Portal 跨帳號資料存取 (HIGH 🔴)
- **發現方式**: Phase 3 (D3a/D3b) + Phase 6 (6.4b)
- **影響**: Portal 使用者可透過 XML-RPC 讀取及修改其他使用者的預約
- **根因**: 缺少 `ir.rule` 記錄規則
- **修復**: 新增 ir.rule 限制 `[('partner_id', '=', user.partner_id.id)]`
- **HTTP 路由**: 不受影響（controller 有 partner_id 檢查）

### BUG-002: POST 無效 resource_id 回傳 500 (MEDIUM 🟡)
- **發現方式**: Phase 7 (7.7b/7.7d)
- **影響**: POST /my/bookings/create with resource_id=99999 → HTTP 500
- **根因**: browse() 不檢查存在性，後續操作觸發未捕獲異常
- **修復**: 新增 `if not resource.exists()` 檢查

### BUG-003: XML 檢視定義順序 (HIGH — 已修復 ✅)
- **發現方式**: 安裝時
- **影響**: 模組無法安裝
- **根因**: Calendar View 引用尚未定義的 Form View
- **修復**: 已調整 XML 順序

## Design Observations (Not Bugs)
| 觀察 | 說明 |
|------|------|
| advance_days 僅 Portal 端驗證 | 後台管理員不受 advance_days 限制 |
| 可用時間僅 Portal 端篩選 | 後台可在非營業時間預約 |
| 已停用資源可被後台預約 | 管理員 override 設計 |
| 非標準時段長度被後台允許 | 例如 1h 時段資源上預約 45min |
| `<img>` 標籤未被 Html sanitizer 移除 | script 被移除但 img 保留 |

## Resources
- GitHub: https://github.com/WOOWTECH/Woow_odoo_internal_booking
- Odoo Calendar Instance: http://localhost:9071
- Addons Path: /var/tmp/vibe-kanban/worktrees/4162-3-odoo-18-porsgr/podman_docker_app/odoo-calendar/addons/
- Test Report: TEST_REPORT.md

---
*Final update: 2026-03-20 12:30*
