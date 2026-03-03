# Odoo Booking Reservation Module

[繁體中文](#繁體中文) | [English](#english)

---

## 繁體中文

### 簡介

Odoo 18 資源預約管理模組，提供完整的資源預約功能，支援後台管理與 Portal 用戶預約。

### 功能特色

- **資源類型管理**：建立並管理可預約的資源（會議室、設備等）
- **資源分類**：使用分類整理不同類型的資源
- **預約管理**：完整的預約建立、編輯、取消功能
- **日曆視圖**：直覺的日曆介面顯示預約狀態
- **Portal 預約**：Portal 用戶可透過網頁介面進行預約
- **授權管理**：管理員可指定哪些聯絡人可以預約特定資源
- **衝突檢測**：自動防止重複預約同一時段
- **Chatter 整合**：完整的訊息與備註功能

### 安裝需求

- Odoo 18.0
- 相依模組：`base`, `mail`, `calendar`, `portal`

### 安裝步驟

1. 將模組放入 Odoo addons 目錄
2. 更新應用程式列表
3. 搜尋「Booking Reservation」並安裝

### 使用說明

#### 後台管理

1. 進入 **Calendar > Resource Bookings** 查看所有預約
2. 進入 **Calendar > Booking Resources** 管理可預約資源
3. 進入 **Calendar > Resource Categories** 管理資源分類
4. 點擊「New」按鈕新增預約

#### Portal 用戶

1. 登入 Portal
2. 進入「My Bookings」查看個人預約
3. 點擊「Book a Resource」進行新預約

### 權限群組

- **Booking Manager**：完整管理權限
- **Portal User**：可預約被授權的資源

### 授權

LGPL-3

### 作者

WOOWTECH - https://woowtech.com

---

## English

### Introduction

Odoo 18 Resource Booking and Reservation Management Module with full backend management and Portal user booking support.

### Features

- **Resource Type Management**: Create and manage bookable resources (meeting rooms, equipment, etc.)
- **Resource Categories**: Organize resources using categories
- **Reservation Management**: Complete booking creation, editing, and cancellation
- **Calendar View**: Intuitive calendar interface showing booking status
- **Portal Booking**: Portal users can book resources through web interface
- **Authorization Management**: Administrators can specify which contacts can book specific resources
- **Conflict Detection**: Automatic prevention of double booking
- **Chatter Integration**: Full messaging and notes functionality

### Requirements

- Odoo 18.0
- Dependencies: `base`, `mail`, `calendar`, `portal`

### Installation

1. Place the module in Odoo addons directory
2. Update the application list
3. Search for "Booking Reservation" and install

### Usage

#### Backend Management

1. Go to **Calendar > Resource Bookings** to view all reservations
2. Go to **Calendar > Booking Resources** to manage bookable resources
3. Go to **Calendar > Resource Categories** to manage resource categories
4. Click "New" button to create a new booking

#### Portal Users

1. Log in to Portal
2. Go to "My Bookings" to view personal reservations
3. Click "Book a Resource" to make a new booking

### User Groups

- **Booking Manager**: Full management access
- **Portal User**: Can book authorized resources

### License

LGPL-3

### Author

WOOWTECH - https://woowtech.com
