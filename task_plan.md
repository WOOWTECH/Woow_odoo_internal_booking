# Task Plan: Odoo Booking Reservation 全面性商用前測試

## Goal
對 WOOWTECH Odoo 18 Booking Reservation 模組進行全面性商用前測試，涵蓋內部/Portal/外部使用者的權限、操作、邊緣事件、暴力測試，確保出廠穩定。

## Current Phase
Phase 8 - 完成 ✅

## 測試環境
- **Odoo 實例**: odoo-calendar-web (port 9071)
- **資料庫**: odoo-calendar-db (PostgreSQL, odoocalendar)
- **帳號**: admin / admin
- **語系**: 繁體中文 (zh_TW)
- **Addons 路徑**: /var/tmp/vibe-kanban/worktrees/4162-3-odoo-18-porsgr/podman_docker_app/odoo-calendar/addons/
- **容器引擎**: Podman
- **GitHub 來源**: https://github.com/WOOWTECH/Woow_odoo_internal_booking (branch: vk/9074-)

## Phases

### Phase 0: 環境準備
- [x] 從 GitHub 下載最新版模組
- [x] 部署到 odoo-calendar 容器的 addons 目錄
- [x] 安裝模組並確認基本啟動
- [x] 建立測試用帳號（Manager / User / Portal）
- **Status:** completed ✅

### Phase 1: 後台管理員 (Manager) 全面測試
- [x] 資源類別 CRUD 測試
- [x] 資源類型 CRUD 測試（含圖片、屬性、可用時間）
- [x] 預約管理 CRUD 測試
- [x] 篩選/搜尋/分組功能測試
- [x] 可用時間 CRUD 測試
- **Status:** completed ✅ (23/23 PASS)

### Phase 2: 內部使用者 (User) 權限測試
- [x] 資源唯讀驗證
- [x] 自己的預約 CRUD 驗證
- [x] 不能刪除他人預約驗證
- [x] 不能修改資源設定驗證
- **Status:** completed ✅ (11/11 PASS)

### Phase 3: Portal 使用者全面測試
- [x] XML-RPC 權限驗證
- [x] 資源瀏覽頁面（/my/booking/resources）
- [x] 資源詳情與時段選擇
- [x] 預約建立流程
- [x] 預約列表與取消
- [x] 存取控制（share_type: all vs specific）
- [x] 隱私保護（不能看到他人預約詳情）
- **Status:** completed ✅ (32/34 — 2 FAIL: BUG-001)

### Phase 4: 邊緣事件與衝突偵測
- [x] 重複預約同一時段（雙重預約衝突）
- [x] 時段邊界測試（結束時間 = 開始時間）
- [x] 已停用資源的預約嘗試
- [x] advance_days 限制測試
- [x] 取消後重新預約同時段
- [x] slot_duration / slot_interval 極端值
- [x] 快速連續預約
- [x] 週末/非可用時間
- **Status:** completed ✅ (29/29 PASS)

### Phase 5: 暴力/壓力測試
- [x] 大量資源建立（100+）
- [x] 大量預約建立（50+）
- [x] 快速連續建立/取消預約
- [x] 大量 Portal 使用者同時存取
- [x] 搜尋效能基準
- **Status:** completed ✅ (11/11 PASS)

### Phase 6: 安全性測試
- [x] SQL 注入嘗試（透過表單欄位）
- [x] XSS 注入嘗試（note/description 欄位）
- [x] CSRF 保護驗證
- [x] 未授權 API 存取（直接打 URL）
- [x] Portal 使用者越權操作
- [x] 直接修改他人預約的嘗試
- **Status:** completed ✅ (23/24 — 1 FAIL: BUG-001)

### Phase 7: UI/UX 與多語系測試
- [x] 繁體中文介面完整性
- [x] 日期時間格式正確性
- [x] 響應式設計（手機版面）
- [x] 錯誤訊息友善度
- [x] 頁面載入速度
- [x] CSS/JS 資源載入
- [x] 表單驗證
- **Status:** completed ✅ (28/30 — 2 FAIL: BUG-002)

### Phase 8: 測試報告彙整
- [x] 彙整所有測試結果
- [x] 列出發現的問題與建議
- [x] 產出正式測試報告
- **Status:** completed ✅

## Key Questions (Answered)
1. ~~模組最新版是否與 odoo-calendar 實例的已安裝模組相容？~~ → 相容（修復 XML 順序後）
2. ~~Portal 使用者需要哪些基本設定才能正常使用？~~ → 需要 Portal 群組 + sel_groups 設定
3. ~~是否有 record rules（記錄規則）限制 Portal/User 的資料存取？~~ → **沒有！這是 BUG-001**

## Decisions Made
| Decision | Rationale |
|----------|-----------|
| 使用 odoo-calendar (9071) 實例 | 已有 calendar, contacts 模組，符合依賴需求 |
| 使用 Podman 而非 Docker | 環境使用 Podman 作為容器引擎 |
| 測試腳本使用 XML-RPC API | 可程式化、可重現、速度快 |
| 5 個 agent 平行執行 Phase 1-7 | 獨立測試階段，可平行加速 |

## Errors Encountered
| Error | Attempt | Resolution |
|-------|---------|------------|
| XML ID not found: view_booking_reservation_form | 1 | 移動 Form View 到 Calendar View 之前 |
| Invalid field 'fields' | 1 | 修正 read() 方法 |
| cannot marshal None | 1 | safe_call_action() helper |
| create() returns list | 1 | OdooRPC.create() 取 [0] |
| Slot interval must be positive | 1 | 修正測試資料 |
| Admin AccessError | 1 | 加入 Booking Manager 群組 |

## Notes
- 所有測試資料保留在實例中供後續參考
- 測試結果記錄在 progress.md
- 發現的問題記錄在 findings.md
- **綜合測試報告: TEST_REPORT.md**
