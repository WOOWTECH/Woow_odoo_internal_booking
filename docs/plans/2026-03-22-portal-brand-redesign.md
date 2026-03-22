# Portal 品牌視覺重設計 PRD

## Woowtech Smart Space Solution — Booking Reservation Portal

**日期**: 2026-03-22
**模組**: odoo_booking_reservation
**範圍**: Portal User 操作頁面品牌視覺優化

---

## 1. 設計原則

- **僅改造模組內容區域**，Odoo Portal 框架（header / footer / nav）保持原生風格
- 嚴格遵循品牌色彩比例：White 50% / Gray 20% / Deep Gray 10% / Blue 10% / Accent 5% / Black 5%
- 字體系統透過 Google Fonts 載入 Outfit，中文 fallback UD Digi Kyokasho
- 所有改動透過 `portal.css` 實現，不修改 Odoo 核心樣式

---

## 2. 品牌色彩系統

### 2.1 主要色彩

| 角色 | HEX | 用途 |
|------|-----|------|
| Primary Blue | `#6183FC` | 主要按鈕、互動元素、品牌強調線 |
| White | `#FFFFFF` | 頁面背景、卡片背景 |
| Light Gray | `#EFF1F5` | 次要背景、卡片邊框、disabled 元素 |
| Gray | `#646262` | 內文文字、次要按鈕、標籤文字 |
| Deep Gray | `#212121` | 標題文字、高對比文字 |

### 2.2 Accent Colors（狀態標籤專用，總佔比 5%）

| 角色 | HEX | 用途 |
|------|-----|------|
| Green | `#8CD37F` | Confirmed 狀態標籤 |
| Coral | `#F45D6D` | Cancelled 狀態標籤、Cancel 按鈕 |
| Yellow | `#F8D158` | Pending 狀態標籤（未來擴展） |
| Cyan | `#7BDBE0` | 使用者已預約時段 |

### 2.3 色彩對應表（現有 → 新設計）

| 元素 | 現有樣式 | 新設計 |
|------|---------|--------|
| 主要按鈕（New Booking、Confirm） | Bootstrap `btn-primary` #0d6efd | `#6183FC` |
| 次要按鈕（Back、Filter、Sort） | Bootstrap `btn-secondary` #6c757d | 白底 + `#646262` 框線 |
| 可用時段按鈕 | `btn-outline-success` 綠框 | 白底 + `#6183FC` 框線 |
| 我的預約時段 | `btn-info` 藍底 | `#7BDBE0` Cyan 填充，白字 |
| 已被預約時段 | `btn-secondary:disabled` 灰色 | `#EFF1F5` 背景，`#646262` 文字 |
| Confirmed 標籤 | `bg-success` Bootstrap 綠 | `#8CD37F` pill 樣式 |
| Cancelled 標籤 | `bg-danger` Bootstrap 紅 | `#F45D6D` pill 樣式 |
| 表格 hover | Bootstrap 淡藍 | `#EFF1F5` Light Gray |
| 連結文字 | Bootstrap `text-primary` | `#6183FC` |
| Focus 邊框 | Bootstrap 預設 | `#6183FC` box-shadow |

---

## 3. 字體系統

### 3.1 字體載入

透過 Google Fonts 載入 Outfit 字型，在 `portal.css` 頂部加入 `@import`：

```css
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;700&display=swap');
```

### 3.2 字體層級

| 層級 | 字體 | 字重 | 大小 | 顏色 | 用途 |
|------|------|------|------|------|------|
| H1 頁面標題 | Outfit | Bold (700) | 1.75rem | `#212121` | 頁面名稱 |
| H2 卡片標題 | Outfit | Medium (500) | 1.25rem | `#212121` | 卡片 header |
| H4 資源名稱 | Outfit | Medium (500) | 1.1rem | `#212121` | 資源/預約名稱 |
| Body 內文 | Outfit | Regular (400) | 0.95rem | `#646262` | 一般文字 |
| DT 標籤 | Outfit | Medium (500) | 0.9rem | `#646262` | 定義列表標籤 |
| DD 內容 | Outfit | Regular (400) | 0.9rem | `#212121` | 定義列表數值 |
| Small 輔助 | Outfit | Light (300) | 0.8rem | `#646262` | 日期、時間、說明 |
| Badge 標籤 | Outfit | Medium (500) | 0.75rem | `#FFFFFF` | 狀態標籤 |

### 3.3 中文 Fallback

```css
font-family: 'Outfit', 'UD Digi Kyokasho', 'Noto Sans TC', sans-serif;
```

---

## 4. 各頁面設計規格

### 4.1 資源列表頁（portal_my_resources）

**路徑**: `/my/booking/resources`

**改造項目**:

| 元素 | 現有 | 新設計 |
|------|------|--------|
| 頁面標題 | Bootstrap h3 | Outfit Bold 1.75rem `#212121` |
| 資源卡片邊框 | Bootstrap card 預設 | `1px solid #EFF1F5` |
| 卡片 hover | translateY -4px + shadow | translateY -2px + `border-bottom: 3px solid #6183FC` + 微陰影 |
| 資源名稱 | Bootstrap card-title | Outfit Medium `#212121` |
| 地點/容量 | Bootstrap text-muted | Outfit Light `#646262` |
| 「Book Now」按鈕 | `btn-primary` Bootstrap | `#6183FC` 背景，border-radius 8px |
| Placeholder icon（無圖片時）| 灰色 | `#6183FC` 品牌藍色 |
| 空狀態訊息 | Bootstrap alert | `#EFF1F5` 背景卡片 + `#646262` 文字 |

### 4.2 資源詳情頁（portal_resource_detail）

**路徑**: `/my/booking/resources/<id>`

**改造項目**:

| 元素 | 現有 | 新設計 |
|------|------|--------|
| 資源資訊卡 | Bootstrap card 預設 | 頂部加 `3px solid #6183FC` 品牌藍頂線 |
| 資源名稱 | Bootstrap h5 | Outfit Bold `#212121` |
| DT 標籤（Location 等）| Bootstrap 預設 | Outfit Medium `#646262` |
| DD 數值 | Bootstrap 預設 | Outfit Regular `#212121` |
| 「Back to Resources」按鈕 | `btn-secondary` | 白底 + `#646262` 框線，hover 填充 `#EFF1F5` |
| 時段卡片 header | Bootstrap card-header | 白底 + 底部 `2px solid #6183FC` |
| 日期導航箭頭 | Bootstrap btn-outline-secondary | `#6183FC` 色，hover 背景 `#EFF1F5` |
| 日期範圍文字 | 預設 | Outfit Medium `#212121` |
| 日期分組標題（2026-03-22）| 預設 bold | Outfit Medium `#212121` 1rem |
| 可用時段按鈕 | `btn-outline-success` 綠框 | 白底 + `1px solid #6183FC` 框線，hover 填充 `#6183FC` 白字 |
| 我的預約時段 | `btn-info` 藍底白字 | `#7BDBE0` Cyan 填充 + 白字，下方小字 "Your booking" |
| 已被預約時段 | `btn-secondary:disabled` 灰 | `#EFF1F5` 背景 + `#646262` 文字，opacity 0.7 |

### 4.3 預約列表頁（portal_my_bookings）

**路徑**: `/my/bookings`

**改造項目**:

| 元素 | 現有 | 新設計 |
|------|------|--------|
| 「New Booking」按鈕 | `btn-primary` Bootstrap | `#6183FC`，border-radius 8px |
| Filter/Sort 按鈕 | `btn-secondary btn-sm` | 白底 + `1px solid #EFF1F5`，文字 `#646262`，hover 背景 `#EFF1F5` |
| Dropdown active 項目 | Bootstrap `bg-primary` | `#6183FC` 背景 |
| **桌面表格** | | |
| 表頭 | Bootstrap 預設 | `#EFF1F5` 背景，Outfit Medium `#646262` |
| 表格行 hover | 淡藍背景 | `#EFF1F5` Light Gray |
| 資源名稱連結 | Bootstrap `text-primary` | `#6183FC`，Outfit Medium |
| View 按鈕 | `btn-sm btn-outline-primary` | `#6183FC` 框線 |
| **手機卡片** | | |
| 卡片 | Bootstrap card | 左側加 `3px` 色條：Confirmed=`#8CD37F`，Cancelled=`#F45D6D` |
| 資源名稱 | `fw-bold text-primary` | Outfit Medium `#212121` |
| 日期/時長 | `text-muted small` | Outfit Light `#646262` |
| **狀態標籤** | | |
| Confirmed | `bg-success` Bootstrap 綠 | `#8CD37F` 背景，白字，pill 樣式 `border-radius: 12px` |
| Cancelled | `bg-danger` Bootstrap 紅 | `#F45D6D` 背景，白字，pill 樣式 |
| 分頁器 | Odoo portal_pager 預設 | Active 頁碼用 `#6183FC` 背景 |

### 4.4 預約詳情頁（portal_booking_detail）

**路徑**: `/my/bookings/<id>`

**改造項目**:

| 元素 | 現有 | 新設計 |
|------|------|--------|
| 主卡片 header | Bootstrap card-header | 白底 + 左邊條 `4px solid #6183FC` |
| 預約編號 | 預設 | Outfit Medium `#212121` |
| 狀態標籤 | Bootstrap badge | 品牌 Accent + pill 樣式（同 4.3） |
| 資源名稱 | h4 預設 | Outfit Bold `#212121` |
| DT 標籤 | 預設 | Outfit Medium `#646262` |
| DD 數值 | 預設 | Outfit Regular `#212121` |
| 「Back」按鈕 | `btn-secondary` | 白底 + `#646262` 框線 |
| 「Cancel Booking」按鈕 | `btn-danger` Bootstrap 紅 | `#F45D6D` Coral 背景，白字 |
| 側邊欄資源卡 | Bootstrap card 預設 | 頂部 `3px solid #6183FC` 品牌藍頂線 |
| 「Book Again」按鈕 | `btn-outline-primary` | `#6183FC` 框線，hover 填充 |
| 成功訊息 Alert | Bootstrap `alert-success` | `#8CD37F` 左邊條 4px + `#EFF1F5` 背景 |
| 取消訊息 Alert | Bootstrap `alert-info` | `#7BDBE0` 左邊條 4px + `#EFF1F5` 背景 |
| 錯誤訊息 Alert | Bootstrap `alert-danger` | `#F45D6D` 左邊條 4px + `#EFF1F5` 背景 |

### 4.5 確認頁（portal_booking_confirm）

**路徑**: `/my/bookings/confirm`

**改造項目**:

| 元素 | 現有 | 新設計 |
|------|------|--------|
| 主卡片 header | Bootstrap card-header | 白底 + 左邊條 `4px solid #6183FC` |
| 資源名稱 | h4 預設 | Outfit Bold `#212121` |
| DT/DD | 預設 | 同 4.4 |
| Note textarea | Bootstrap 預設 | 邊框 `#EFF1F5`，focus 時 `#6183FC` + box-shadow |
| 「Back」按鈕 | `btn-secondary` | 白底 + `#646262` 框線 |
| 「Confirm Booking」按鈕 | `btn-primary` | `#6183FC`，加大 padding（py-2 px-4），border-radius 8px |
| 側邊欄 | 同 4.4 | 同 4.4 |

### 4.6 Portal 首頁卡片（portal_my_home_booking）

**改造項目**:

| 元素 | 現有 | 新設計 |
|------|------|--------|
| 卡片 icon | 預設 | `#6183FC` 品牌藍 |
| 卡片標題 | 預設 | Outfit Medium `#212121` |
| 卡片說明文字 | 預設 | Outfit Regular `#646262` |

---

## 5. 實作方式

### 5.1 修改檔案

| 檔案 | 修改內容 |
|------|---------|
| `static/src/css/portal.css` | 完整重寫品牌樣式，載入 Outfit 字型 |
| `views/portal_templates.xml` | 更新部分 CSS class（badge pill、卡片色條、alert 樣式） |

### 5.2 CSS 變數定義

在 `portal.css` 頂部定義品牌 CSS 變數，方便日後維護：

```css
:root {
    --ws-primary: #6183FC;
    --ws-white: #FFFFFF;
    --ws-light-gray: #EFF1F5;
    --ws-gray: #646262;
    --ws-deep-gray: #212121;
    --ws-cyan: #7BDBE0;
    --ws-green: #8CD37F;
    --ws-coral: #F45D6D;
    --ws-yellow: #F8D158;
    --ws-font: 'Outfit', 'UD Digi Kyokasho', 'Noto Sans TC', sans-serif;
}
```

### 5.3 不修改的部分

- Odoo Portal 框架（header、footer、navigation sidebar）
- Bootstrap 基礎 grid 系統
- RWD 響應式斷點邏輯（已在前次優化中完成）
- JavaScript 互動邏輯
- Controller 路由邏輯

---

## 6. 品牌色彩比例驗證

| 色彩 | 目標比例 | 實際應用 |
|------|---------|---------|
| White `#FFFFFF` | 50% | 頁面背景、卡片背景、按鈕底色 |
| Gray `#646262` | 20% | 內文文字、標籤、次要按鈕框線、輔助資訊 |
| Deep Gray `#212121` | 10% | 標題、資源名稱、數值、高對比文字 |
| Blue `#6183FC` | 10% | 主要按鈕、時段選擇、品牌強調線、連結、focus 狀態 |
| Accent Colors | 5% | 狀態標籤（Green/Coral/Yellow）、Cyan 已預約時段 |
| Black | 5% | Odoo 框架元素（非本次修改範圍） |
