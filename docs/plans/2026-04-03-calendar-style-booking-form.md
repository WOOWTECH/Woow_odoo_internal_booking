# 日曆風格預定表單重構設計

**日期**: 2026-04-03
**狀態**: 待實作

---

## 1. 目標

將 Booking Reservation 的後台表單與 Portal 確認頁面改造為 Odoo Calendar 風格，新增主題標題、舉辦方、參加者、Discussion 通道整合、說明欄位，並完成中文化。

## 2. 範圍

- Backend Admin 表單 (booking_reservation_views.xml)
- Portal 確認頁面 (portal_templates.xml — portal_booking_confirm)
- Portal 預定詳情頁面
- 資源設定表單 (booking_resource_type_views.xml)
- 中文化 (i18n/zh_TW.po) — 後台 + Portal 全面覆蓋

## 3. 不包含

- 循環預定 (Recurrence) — 後續另案處理
- 全天事件 (All Day) — 資源預訂場景不常用，暫不做

---

## 4. 資料模型變更

### 4.1 booking.reservation — 新增欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| `subject` | Char | 預定主題，顯示在表單頂部 |
| `description` | Html | 說明（取代 `note`） |
| `organizer_id` | Many2one → res.partner | 舉辦方，預設=建立者 |
| `attendee_ids` | Many2many → res.partner | 參加者列表 |
| `enable_discussion` | Boolean | 是否開啟討論通道 |
| `channel_id` | Many2one → discuss.channel | 關聯的 Discussion 通道 |
| `reminder_type` | Selection | 提醒方式：none/notification/email |
| `reminder_time` | Integer | 提前提醒時間（分鐘） |

### 4.2 booking.reservation — 欄位調整

- `duration`: 改為可手動輸入，與 `end_datetime` 雙向同步
  - 修改 duration → 自動算 end_datetime
  - 修改 end_datetime → 自動算 duration
- `name`: 有 subject 時用 subject，否則用原本的 `{resource} - {datetime}`
- `note`: 保留欄位，新資料寫入 `description`

### 4.3 booking.resource.type — 新增欄位

| 欄位 | 類型 | 說明 |
|------|------|------|
| `enable_discussion` | Boolean | 允許此資源的預定開啟討論通道 |

### 4.4 Discussion 通道邏輯

前提：資源的 `enable_discussion` = True

1. 使用者預定時看到「☐ 開啟討論通道」選項
2. 勾選後儲存/確認時，自動建立 `discuss.channel`
3. 通道名稱 = `[資源名] 主題` 或 `[資源名] 預定時間`
4. 自動加入 organizer + 所有 attendees 為 channel members
5. Portal 使用者透過 `cs_portal_discuss` 模組存取通道

依賴：`cs_portal_discuss` 作為 optional dependency，若未安裝則 Discussion 功能完全隱藏。

---

## 5. Backend Admin 表單

```
┌──────────────────────────────────────────────────┐
│ header: [確認] [取消]  statusbar: confirmed/cancelled │
├──────────────────────────────────────────────────┤
│ [subject] 預定主題（大字 nolabel，placeholder:"例如:部門週會"） │
│                                                    │
│ 資源        [resource_type_id]                      │
│                                                    │
│ ── 資源資訊（選了資源後顯示）─────────                  │
│ │ 地點: Building 1, Floor 3                         │
│ │ 容量: 10 人                                       │
│ │ 說明: ...                                         │
│ └──────────────────────────────────                │
│                                                    │
│ 開始   [start_datetime]  →  [end_datetime]          │
│ 時長   [duration] 小時                               │
│                                                    │
│ 舉辦方      [organizer_id]                          │
│ 參加者      [attendee_ids] (many2many_tags)          │
│                                                    │
│ ── 討論通道（資源允許時顯示）─────────                  │
│ │ ☐ 開啟討論通道                                     │
│ │ 通道連結: [channel_id] (勾選後顯示)                 │
│ └──────────────────────────────────                │
│                                                    │
│ ── 說明 ──────────────────────                      │
│ [description] (Html editor)                         │
│                                                    │
│ ── 提醒 ──────────────────────                      │
│ [reminder_type] [reminder_time]                     │
├──────────────────────────────────────────────────┤
│ Chatter                                            │
└──────────────────────────────────────────────────┘
```

---

## 6. Portal 確認頁面

```
┌──────────────────────────────────────────────────┐
│ 確認預定                                           │
├──────────────────────────────────────────────────┤
│ 預定主題    [________________] (可選填)              │
│                                                    │
│ ── 資源資訊 ──────────────────                      │
│ 資源        Conference Room A                       │
│ 地點        Building 1, Floor 3                     │
│ 容量        10 人                                   │
│                                                    │
│ ── 時間 ──────────────────────                      │
│ 開始        2026-04-03 14:00                        │
│ 結束        2026-04-03 15:00                        │
│ 時長        1 小時                                   │
│ （時間唯讀，由時段頁面帶入）                           │
│                                                    │
│ 舉辦方      Portal User 1 (自動帶入，唯讀)            │
│ 參加者      [選擇參加者...] (多選)                    │
│                                                    │
│ ☐ 開啟討論通道 （資源允許時才顯示）                    │
│                                                    │
│ 說明        [_________________] (可選填)              │
│                                                    │
│         [返回]  [確認預定]                            │
└──────────────────────────────────────────────────┘
```

---

## 7. 資源設定表單新增

在 booking.resource.type 表單中新增：

```
── 進階設定 ──────────────
☐ 允許討論通道    （勾選後，預定此資源時可選擇開啟 Discussion）
```

---

## 8. 中文化 (i18n/zh_TW.po)

### 8.1 後台欄位

| 英文 | 中文 |
|------|------|
| Subject | 預定主題 |
| Start | 開始 |
| End | 結束 |
| Duration | 時長 |
| Organizer | 舉辦方 |
| Attendees | 參加者 |
| Enable Discussion | 開啟討論通道 |
| Discussion Channel | 討論通道 |
| Description | 說明 |
| Reminder | 提醒 |
| Resource | 資源 |
| Resource Info | 資源資訊 |
| Location | 地點 |
| Capacity | 容量 |
| Confirm | 確認 |
| Cancel | 取消 |
| Confirmed | 已確認 |
| Cancelled | 已取消 |
| Booking Details | 預定詳情 |
| Contact | 聯絡人 |
| Notes | 備註 |
| Booked By | 預定者 |
| Select Resource | 選擇資源 |
| Additional notes or requirements... | 備註說明... |
| Are you sure you want to cancel this booking? | 確定要取消此預定嗎？ |

### 8.2 Portal 頁面

| 英文 | 中文 |
|------|------|
| My Bookings | 我的預定 |
| Book Resources | 預定資源 |
| View and manage your resource reservations | 查看及管理您的資源預定 |
| Browse and book available resources | 瀏覽並預定可用資源 |
| Available Time Slots | 可用時段 |
| Booking Summary | 預定摘要 |
| Confirm Booking | 確認預定 |
| Back | 返回 |
| View Available Slots | 查看可用時段 |
| No Resources Available | 目前沒有可用資源 |
| Your booking has been confirmed! | 您的預定已確認！ |
| Enable Discussion Channel | 開啟討論通道 |
| Select attendees... | 選擇參加者... |
| e.g. Department Weekly Meeting | 例如：部門週會 |

---

## 9. 依賴關係

### __manifest__.py 更新

```python
'depends': [
    'base',
    'mail',
    'calendar',
    'portal',
],
```

不新增硬依賴。`cs_portal_discuss` 為軟依賴：
- 安裝時 Discussion 功能完整可用（Portal 使用者可存取通道）
- 未安裝時 Discussion 欄位/按鈕在後台仍可用，但 Portal 使用者看不到通道連結

---

## 10. 實作順序

1. Model 變更 — booking_reservation.py 新增欄位 + 邏輯
2. Model 變更 — booking_resource_type.py 新增 enable_discussion
3. Backend Views — booking_reservation_views.xml 重構表單
4. Backend Views — booking_resource_type_views.xml 加入 enable_discussion
5. Portal Controller — portal.py 更新確認/建立邏輯
6. Portal Templates — portal_templates.xml 重構確認頁面 + 詳情頁面
7. Discussion 整合 — 自動建立 channel 邏輯
8. 中文化 — i18n/zh_TW.po
9. 部署測試
10. Commit & Push
