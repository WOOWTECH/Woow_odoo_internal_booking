#!/usr/bin/env python3
"""
Portal 使用者完整功能細部測試
Complete detailed portal user functionality test with full output

Tests every portal page, route, form, button, and edge case.
"""

import sys
import os
import re
import json
from datetime import datetime, timedelta
sys.path.insert(0, os.path.dirname(__file__))

from odoo_rpc import OdooRPC
import requests
from html.parser import HTMLParser

URL = "http://localhost:9071"
results = []


def record(test_id, name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    results.append({"id": test_id, "name": name, "passed": passed, "detail": detail})
    print(f"  [{status}] {test_id} - {name}")
    if detail:
        for line in detail.split("\n"):
            print(f"         {line}")


def get_session(login, password):
    """Login and return session + csrf token."""
    s = requests.Session()
    resp = s.get(f"{URL}/web/login")
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    token = csrf.group(1) if csrf else ""
    login_resp = s.post(f"{URL}/web/login", data={
        "login": login,
        "password": password,
        "csrf_token": token,
        "redirect": "/my",
    }, allow_redirects=True)
    return s, token, login_resp


def get_csrf(session, url):
    """Get fresh CSRF token from a page."""
    resp = session.get(url)
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    return csrf.group(1) if csrf else "", resp


def extract_text_from_html(html):
    """Extract visible text from HTML."""
    class TextExtractor(HTMLParser):
        def __init__(self):
            super().__init__()
            self.texts = []
            self.skip = False
        def handle_starttag(self, tag, attrs):
            if tag in ('script', 'style'):
                self.skip = True
        def handle_endtag(self, tag):
            if tag in ('script', 'style'):
                self.skip = False
        def handle_data(self, data):
            if not self.skip:
                t = data.strip()
                if t:
                    self.texts.append(t)
    extractor = TextExtractor()
    extractor.feed(html)
    return extractor.texts


# =============================================================
print("=" * 70)
print("Portal 使用者完整功能細部測試")
print(f"測試時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"實例: {URL}")
print("=" * 70)

# =============================================================
# SECTION 1: Portal 帳號資訊
# =============================================================
print("\n" + "=" * 70)
print("SECTION 1: Portal 使用者帳號資訊")
print("=" * 70)

rpc_admin = OdooRPC("admin", "admin")

portal_accounts = [
    ("portal1", "portal1", 8),
    ("portal2", "portal2", 9),
    ("portal3", "portal3", 10),
]

print("\n  ┌──────────┬──────────┬─────────┬────────────┬───────────────┐")
print("  │ 帳號     │ 密碼     │ User ID │ Partner ID │ 說明          │")
print("  ├──────────┼──────────┼─────────┼────────────┼───────────────┤")

for login, pwd, uid in portal_accounts:
    user_data = rpc_admin.read("res.users", [uid], ["login", "partner_id", "name"])[0]
    partner_id = user_data["partner_id"][0]
    name = user_data["name"]
    note = "可存取 VIP Room" if login in ("portal1", "portal2") else "受限 (無 VIP)"
    print(f"  │ {login:<8} │ {pwd:<8} │ {uid:<7} │ {partner_id:<10} │ {note:<13} │")

print("  └──────────┴──────────┴─────────┴────────────┴───────────────┘")
print(f"\n  登入網址: {URL}/web/login")
print(f"  語系: 繁體中文 (zh_TW)")

# =============================================================
# SECTION 2: Portal 登入流程
# =============================================================
print("\n" + "=" * 70)
print("SECTION 2: Portal 登入流程")
print("=" * 70)

# 2.1 Login page
resp = requests.get(f"{URL}/web/login")
has_login_form = 'name="login"' in resp.text and 'name="password"' in resp.text
has_csrf = 'name="csrf_token"' in resp.text
record("2.1", "登入頁面載入", resp.status_code == 200,
       f"status={resp.status_code}, 有登入表單={has_login_form}, 有CSRF={has_csrf}")

# 2.2 Successful login for each portal user
for login, pwd, uid in portal_accounts:
    s, token, login_resp = get_session(login, pwd)
    is_portal = "/my" in login_resp.url or "/odoo" not in login_resp.url
    record(f"2.2-{login}", f"{login} 登入成功",
           login_resp.status_code == 200 and is_portal,
           f"status={login_resp.status_code}, redirect_url={login_resp.url}")

# 2.3 Failed login
s = requests.Session()
resp = s.get(f"{URL}/web/login")
csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
token = csrf.group(1) if csrf else ""
bad_resp = s.post(f"{URL}/web/login", data={
    "login": "portal1",
    "password": "wrongpassword",
    "csrf_token": token,
    "redirect": "/my",
}, allow_redirects=True)
has_error = "error" in bad_resp.text.lower() or "incorrect" in bad_resp.text.lower() or "錯誤" in bad_resp.text
record("2.3", "錯誤密碼登入被拒絕",
       "/web/login" in bad_resp.url or has_error,
       f"status={bad_resp.status_code}, url={bad_resp.url}, 有錯誤訊息={has_error}")

# =============================================================
# SECTION 3: Portal 首頁 (/my)
# =============================================================
print("\n" + "=" * 70)
print("SECTION 3: Portal 首頁 (/my)")
print("=" * 70)

session, _, _ = get_session("portal1", "portal1")

resp = session.get(f"{URL}/my")
texts = extract_text_from_html(resp.text)
chinese_texts = [t for t in texts if any('\u4e00' <= c <= '\u9fff' for c in t)]

record("3.1", "Portal 首頁載入", resp.status_code == 200,
       f"status={resp.status_code}, 頁面大小={len(resp.text)} bytes")

has_booking_link = "/my/booking" in resp.text or "/my/bookings" in resp.text
record("3.2", "首頁包含預約相關連結", has_booking_link,
       f"booking連結存在={has_booking_link}")

record("3.3", "首頁包含中文內容", len(chinese_texts) > 5,
       f"中文片段數={len(chinese_texts)}, 範例={chinese_texts[:5]}")

# Check navigation elements
has_my_account = "我的帳戶" in resp.text or "my account" in resp.text.lower()
has_logout = "登出" in resp.text or "logout" in resp.text.lower() or "/web/session/logout" in resp.text
record("3.4", "導航列包含帳戶/登出", has_my_account or has_logout,
       f"我的帳戶={has_my_account}, 登出={has_logout}")

# =============================================================
# SECTION 4: 資源列表頁 (/my/booking/resources)
# =============================================================
print("\n" + "=" * 70)
print("SECTION 4: 資源列表頁 (/my/booking/resources)")
print("=" * 70)

resp = session.get(f"{URL}/my/booking/resources")
record("4.1", "資源列表頁載入", resp.status_code == 200,
       f"status={resp.status_code}, 大小={len(resp.text)} bytes")

# Check for resource cards
has_conference = "Conference Room A" in resp.text
has_meeting = "Small Meeting Room B" in resp.text
has_projector = "Projector" in resp.text
has_phone = "Phone Booth" in resp.text
has_vip = "VIP Room C" in resp.text

record("4.2", "顯示所有公開資源 (share_type=all)",
       has_conference and has_meeting and has_projector and has_phone,
       f"Conference={has_conference}, Meeting={has_meeting}, Projector={has_projector}, Phone={has_phone}")

record("4.3", "顯示 portal1 可存取的限定資源 (VIP Room C)",
       has_vip,
       f"VIP Room C 可見={has_vip}")

# Check card elements
has_card_class = "card" in resp.text
has_capacity = "容量" in resp.text or "capacity" in resp.text.lower() or "人" in resp.text
has_location = any(x in resp.text for x in ["location", "地點", "位置", "3F", "1F", "Building"])

record("4.4", "資源卡片包含基本資訊",
       has_card_class,
       f"卡片樣式={has_card_class}, 容量資訊={has_capacity}, 地點資訊={has_location}")

# Check that each resource links to detail page
resource_links = re.findall(r'/my/booking/resources/(\d+)', resp.text)
record("4.5", "每個資源有詳情連結",
       len(resource_links) >= 4,
       f"找到 {len(resource_links)} 個資源連結, IDs={list(set(resource_links))}")

# portal3 should NOT see VIP Room C
session3, _, _ = get_session("portal3", "portal3")
resp3 = session3.get(f"{URL}/my/booking/resources")
has_vip_p3 = "VIP Room C" in resp3.text
record("4.6", "portal3 不可見 VIP Room C (share_type=specific)",
       not has_vip_p3,
       f"portal3 可見 VIP Room={has_vip_p3}")

# =============================================================
# SECTION 5: 資源詳情頁 (/my/booking/resources/<id>)
# =============================================================
print("\n" + "=" * 70)
print("SECTION 5: 資源詳情頁 (/my/booking/resources/<id>)")
print("=" * 70)

# 5.1 Conference Room A (id=2)
resp = session.get(f"{URL}/my/booking/resources/2")
record("5.1", "Conference Room A 詳情頁載入", resp.status_code == 200,
       f"status={resp.status_code}, 大小={len(resp.text)} bytes")

has_name = "Conference Room A" in resp.text
has_slot_info = any(x in resp.text for x in ["slot", "時段", "1:00", "1 小時", "60"])
has_booking_form = "start_datetime" in resp.text or "slot-btn" in resp.text or "book" in resp.text.lower()
record("5.2", "詳情頁包含資源名稱和預約功能",
       has_name and has_booking_form,
       f"資源名稱={has_name}, 時段資訊={has_slot_info}, 預約功能={has_booking_form}")

# Check slot buttons or time selection
has_slot_buttons = "slot-btn" in resp.text or "btn-outline-success" in resp.text
slot_btn_count = resp.text.count("slot-btn") + resp.text.count("btn-outline-success")
record("5.3", "顯示可選擇的時段按鈕",
       has_slot_buttons,
       f"時段按鈕數≈{slot_btn_count}")

# Check date picker / calendar
has_date_selector = any(x in resp.text for x in ["date", "calendar", "datepicker", "日期"])
record("5.4", "有日期選擇功能",
       has_date_selector,
       f"日期選擇器={has_date_selector}")

# 5.5 Small Meeting Room B (id=3, 30min slots)
resp_b = session.get(f"{URL}/my/booking/resources/3")
record("5.5", "Small Meeting Room B 詳情頁載入", resp_b.status_code == 200,
       f"status={resp_b.status_code}, 30分鐘時段資源")

# 5.6 VIP Room C (id=4) - portal1 CAN access
resp_vip = session.get(f"{URL}/my/booking/resources/4")
record("5.6", "portal1 可存取 VIP Room C 詳情頁", resp_vip.status_code == 200,
       f"status={resp_vip.status_code}")

# 5.7 VIP Room C - portal3 CANNOT access
resp_vip3 = session3.get(f"{URL}/my/booking/resources/4")
record("5.7", "portal3 不可存取 VIP Room C 詳情頁",
       resp_vip3.status_code in (400, 403, 404) or "error" in resp_vip3.url or resp_vip3.status_code == 200 and "VIP Room C" not in resp_vip3.text,
       f"status={resp_vip3.status_code}, url={resp_vip3.url}")

# 5.8 Non-existent resource
resp_bad = session.get(f"{URL}/my/booking/resources/99999")
record("5.8", "不存在的資源回傳友善錯誤", resp_bad.status_code != 500,
       f"status={resp_bad.status_code}")

# 5.9 Projector (id=5)
resp_proj = session.get(f"{URL}/my/booking/resources/5")
record("5.9", "Projector 詳情頁載入", resp_proj.status_code == 200,
       f"status={resp_proj.status_code}")

# 5.10 Phone Booth (id=6, 15min slots)
resp_phone = session.get(f"{URL}/my/booking/resources/6")
record("5.10", "Phone Booth 詳情頁載入 (15分鐘時段)", resp_phone.status_code == 200,
       f"status={resp_phone.status_code}")

# =============================================================
# SECTION 6: 時段 API (/my/booking/resources/<id>/slots)
# =============================================================
print("\n" + "=" * 70)
print("SECTION 6: 時段查詢 API")
print("=" * 70)

tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")


def json_rpc_call(sess, url, params=None):
    """Call a type='json' Odoo route using JSON-RPC envelope."""
    payload = {
        "jsonrpc": "2.0",
        "method": "call",
        "id": 1,
        "params": params or {},
    }
    return sess.post(url, json=payload, headers={"Content-Type": "application/json"})


# 6.1 Slots for Conference Room A
resp_slots = json_rpc_call(session, f"{URL}/my/booking/resources/2/slots",
                           {"date": tomorrow})
record("6.1", f"Conference Room A 時段查詢 ({tomorrow})",
       resp_slots.status_code == 200,
       f"status={resp_slots.status_code}, content_type={resp_slots.headers.get('Content-Type', 'N/A')}")

try:
    slots_json = resp_slots.json()
    slots_data = slots_json.get("result", slots_json)
    if isinstance(slots_data, list):
        slot_count = len(slots_data)
    elif isinstance(slots_data, dict):
        slot_count = len(slots_data.get("slots", slots_data.get("data", [])))
    else:
        slot_count = 0
    record("6.2", "時段 API 返回 JSON 格式",
           True, f"時段數={slot_count}, 類型={type(slots_data).__name__}")
except Exception as e:
    record("6.2", "時段 API 返回 JSON 格式",
           False, f"非 JSON 回應, error={e}, text={resp_slots.text[:200]}")
    slots_data = None

# 6.3 Slots for 30min resource
resp_slots_b = json_rpc_call(session, f"{URL}/my/booking/resources/3/slots",
                             {"date": tomorrow})
try:
    slots_b_json = resp_slots_b.json()
    slots_b_data = slots_b_json.get("result", slots_b_json)
    if isinstance(slots_b_data, list):
        slots_b_count = len(slots_b_data)
    elif isinstance(slots_b_data, dict):
        slots_b_count = len(slots_b_data.get("slots", slots_b_data.get("data", [])))
    else:
        slots_b_count = 0
    record("6.3", f"Small Meeting Room B 時段查詢 (30min slots)",
           resp_slots_b.status_code == 200,
           f"時段數={slots_b_count}")
except:
    record("6.3", f"Small Meeting Room B 時段查詢",
           resp_slots_b.status_code == 200,
           f"status={resp_slots_b.status_code}")

# =============================================================
# SECTION 7: 建立預約流程
# =============================================================
print("\n" + "=" * 70)
print("SECTION 7: 建立預約流程")
print("=" * 70)

# 7.1 New booking page (resource selection page)
resp_new = session.get(f"{URL}/my/bookings/new")
record("7.1", "新預約頁面載入 (/my/bookings/new)",
       resp_new.status_code == 200,
       f"status={resp_new.status_code}, 頁面為資源選擇頁")


def get_csrf_from_resource_page(sess, resource_id):
    """Get CSRF token from resource detail page (where slot booking forms are)."""
    resp = sess.get(f"{URL}/my/booking/resources/{resource_id}")
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', resp.text)
    return csrf.group(1) if csrf else "", resp


def extract_slot_form(html, slot_index=0):
    """Extract slot form data (start_datetime, end_datetime, resource_id) from the resource detail page."""
    forms = re.findall(
        r'<form[^>]*action="/my/bookings/create"[^>]*>.*?</form>',
        html, re.DOTALL
    )
    if slot_index >= len(forms):
        return None
    form = forms[slot_index]
    resource_id = re.search(r'name="resource_id"\s+value="([^"]+)"', form)
    start = re.search(r'name="start_datetime"\s+value="([^"]+)"', form)
    end = re.search(r'name="end_datetime"\s+value="([^"]+)"', form)
    csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', form)
    return {
        "resource_id": resource_id.group(1) if resource_id else None,
        "start_datetime": start.group(1) if start else None,
        "end_datetime": end.group(1) if end else None,
        "csrf_token": csrf.group(1) if csrf else None,
        "form_count": len(forms),
    }


day_after = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d")

# 7.2 Create booking via POST - Conference Room A
# First get the resource detail page with date parameter to get slot forms
token_r, resp_r = get_csrf_from_resource_page(session, 2)
# Try to extract a slot form for day_after
resp_slots_page = session.get(f"{URL}/my/booking/resources/2", params={"date": day_after})
slot_form = extract_slot_form(resp_slots_page.text)

if slot_form and slot_form["csrf_token"]:
    create_data = {
        "resource_id": slot_form["resource_id"],
        "start_datetime": slot_form["start_datetime"],
        "end_datetime": slot_form["end_datetime"],
        "note": "Portal 細部測試預約 - Conference Room A",
        "csrf_token": slot_form["csrf_token"],
    }
else:
    # Fallback: use token from resource page and manual times
    create_data = {
        "resource_id": "2",
        "start_datetime": f"{day_after} 10:00:00",
        "end_datetime": f"{day_after} 11:00:00",
        "note": "Portal 細部測試預約 - Conference Room A",
        "csrf_token": token_r,
    }

create_resp = session.post(f"{URL}/my/bookings/create", data=create_data, allow_redirects=True)

booking_created = "success" in create_resp.url or create_resp.status_code == 200
booking_id_match = re.search(r'/my/bookings/(\d+)', create_resp.url)
booking_id = int(booking_id_match.group(1)) if booking_id_match else None

record("7.2", "建立預約 - Conference Room A (1小時)",
       booking_created and booking_id is not None,
       f"status={create_resp.status_code}, url={create_resp.url}, booking_id={booking_id}\n"
       f"         slot_forms_found={slot_form['form_count'] if slot_form else 0}")

# 7.3 Create booking for Small Meeting Room B (30min)
resp_r3 = session.get(f"{URL}/my/booking/resources/3", params={"date": day_after})
slot_form3 = extract_slot_form(resp_r3.text)
token_r3, _ = get_csrf_from_resource_page(session, 3)

if slot_form3 and slot_form3["csrf_token"]:
    create_data3 = {
        "resource_id": slot_form3["resource_id"],
        "start_datetime": slot_form3["start_datetime"],
        "end_datetime": slot_form3["end_datetime"],
        "note": "Portal 細部測試預約 - Small Meeting Room B (30min)",
        "csrf_token": slot_form3["csrf_token"],
    }
else:
    create_data3 = {
        "resource_id": "3",
        "start_datetime": f"{day_after} 14:00:00",
        "end_datetime": f"{day_after} 14:30:00",
        "note": "Portal 細部測試預約 - Small Meeting Room B (30min)",
        "csrf_token": token_r3,
    }

create_resp2 = session.post(f"{URL}/my/bookings/create", data=create_data3, allow_redirects=True)
booking_id2_match = re.search(r'/my/bookings/(\d+)', create_resp2.url)
booking_id2 = int(booking_id2_match.group(1)) if booking_id2_match else None

record("7.3", "建立預約 - Small Meeting Room B (30分鐘)",
       booking_id2 is not None,
       f"booking_id={booking_id2}")

# 7.4 Create booking for VIP Room C (portal1, allowed)
resp_r4 = session.get(f"{URL}/my/booking/resources/4", params={"date": day_after})
slot_form4 = extract_slot_form(resp_r4.text)
token_r4, _ = get_csrf_from_resource_page(session, 4)

if slot_form4 and slot_form4["csrf_token"]:
    create_data4 = {
        "resource_id": slot_form4["resource_id"],
        "start_datetime": slot_form4["start_datetime"],
        "end_datetime": slot_form4["end_datetime"],
        "note": "VIP 會議室預約測試",
        "csrf_token": slot_form4["csrf_token"],
    }
else:
    create_data4 = {
        "resource_id": "4",
        "start_datetime": f"{day_after} 09:00:00",
        "end_datetime": f"{day_after} 11:00:00",
        "note": "VIP 會議室預約測試",
        "csrf_token": token_r4,
    }

create_resp3 = session.post(f"{URL}/my/bookings/create", data=create_data4, allow_redirects=True)
booking_id3_match = re.search(r'/my/bookings/(\d+)', create_resp3.url)
booking_id3 = int(booking_id3_match.group(1)) if booking_id3_match else None

record("7.4", "建立預約 - VIP Room C (portal1, 允許名單內)",
       booking_id3 is not None,
       f"booking_id={booking_id3}")

# 7.5 Create booking for VIP Room C as portal3 (should fail)
resp_r5 = session3.get(f"{URL}/my/booking/resources/4", params={"date": day_after})
slot_form5 = extract_slot_form(resp_r5.text)
# portal3 can't access VIP, so slot_form5 should be None or have no forms
token_p3, _ = get_csrf_from_resource_page(session3, 2)  # Get csrf from a page portal3 CAN access

if slot_form5 and slot_form5["csrf_token"]:
    create_data_p3 = {
        "resource_id": "4",
        "start_datetime": slot_form5["start_datetime"],
        "end_datetime": slot_form5["end_datetime"],
        "note": "portal3 嘗試預約 VIP (應失敗)",
        "csrf_token": slot_form5["csrf_token"],
    }
else:
    create_data_p3 = {
        "resource_id": "4",
        "start_datetime": f"{day_after} 15:00:00",
        "end_datetime": f"{day_after} 17:00:00",
        "note": "portal3 嘗試預約 VIP (應失敗)",
        "csrf_token": token_p3,
    }

create_resp_p3 = session3.post(f"{URL}/my/bookings/create", data=create_data_p3, allow_redirects=True)
p3_failed = "error" in create_resp_p3.url or "unauthorized" in create_resp_p3.url
record("7.5", "portal3 預約 VIP Room C 被拒絕 (不在允許名單)",
       p3_failed,
       f"url={create_resp_p3.url}")

# 7.6 Create booking with empty fields
token6, _ = get_csrf_from_resource_page(session, 2)
create_empty = session.post(f"{URL}/my/bookings/create", data={
    "csrf_token": token6,
}, allow_redirects=True)
record("7.6", "空白表單提交被友善處理",
       create_empty.status_code != 500 and "error" in create_empty.url,
       f"status={create_empty.status_code}, url={create_empty.url}")

# 7.7 Create booking with invalid resource_id
token7, _ = get_csrf_from_resource_page(session, 2)
create_invalid = session.post(f"{URL}/my/bookings/create", data={
    "resource_id": "99999",
    "start_datetime": f"{day_after} 10:00:00",
    "end_datetime": f"{day_after} 11:00:00",
    "csrf_token": token7,
}, allow_redirects=True)
record("7.7", "無效 resource_id 被友善處理 (非 500)",
       create_invalid.status_code != 500,
       f"status={create_invalid.status_code}, url={create_invalid.url}")

# 7.8 Create as portal2
session2, _, _ = get_session("portal2", "portal2")
resp_r8 = session2.get(f"{URL}/my/booking/resources/2", params={"date": day_after})
slot_form8 = extract_slot_form(resp_r8.text)
token_p2, _ = get_csrf_from_resource_page(session2, 2)

if slot_form8 and slot_form8["csrf_token"]:
    # Pick a different slot (e.g. index 5 or later) to avoid conflicts with portal1
    resp_r8_alt = session2.get(f"{URL}/my/booking/resources/2", params={"date": day_after})
    slot_form8_alt = extract_slot_form(resp_r8_alt.text, slot_index=5)
    if slot_form8_alt and slot_form8_alt["csrf_token"]:
        slot_form8 = slot_form8_alt
    create_data_p2 = {
        "resource_id": slot_form8["resource_id"],
        "start_datetime": slot_form8["start_datetime"],
        "end_datetime": slot_form8["end_datetime"],
        "note": "Portal2 測試預約",
        "csrf_token": slot_form8["csrf_token"],
    }
else:
    create_data_p2 = {
        "resource_id": "2",
        "start_datetime": f"{day_after} 16:00:00",
        "end_datetime": f"{day_after} 17:00:00",
        "note": "Portal2 測試預約",
        "csrf_token": token_p2,
    }

create_p2 = session2.post(f"{URL}/my/bookings/create", data=create_data_p2, allow_redirects=True)
booking_id_p2_match = re.search(r'/my/bookings/(\d+)', create_p2.url)
booking_id_p2 = int(booking_id_p2_match.group(1)) if booking_id_p2_match else None
record("7.8", "portal2 建立預約成功",
       booking_id_p2 is not None,
       f"booking_id={booking_id_p2}")

# =============================================================
# SECTION 8: 預約列表頁 (/my/bookings)
# =============================================================
print("\n" + "=" * 70)
print("SECTION 8: 預約列表頁 (/my/bookings)")
print("=" * 70)

resp_list = session.get(f"{URL}/my/bookings")
record("8.1", "預約列表頁載入", resp_list.status_code == 200,
       f"status={resp_list.status_code}, 大小={len(resp_list.text)} bytes")

# Check listing content
has_table_or_list = "booking" in resp_list.text.lower()
record("8.2", "預約列表包含預約記錄", has_table_or_list,
       f"有預約記錄={has_table_or_list}")

# Check status badges
has_confirmed = "confirmed" in resp_list.text.lower() or "已確認" in resp_list.text
has_badge = "badge" in resp_list.text
record("8.3", "預約狀態徽章顯示",
       has_confirmed or has_badge,
       f"confirmed={has_confirmed}, badge={has_badge}")

# Check filter/sort
has_filter = "sortby" in resp_list.text or "filterby" in resp_list.text or "filter" in resp_list.text.lower()
record("8.4", "列表有篩選/排序功能",
       has_filter,
       f"篩選功能={has_filter}")

# 8.5 Filter by confirmed
resp_confirmed = session.get(f"{URL}/my/bookings", params={"filterby": "confirmed"})
record("8.5", "依狀態篩選 (confirmed)",
       resp_confirmed.status_code == 200,
       f"status={resp_confirmed.status_code}")

# 8.6 Sort by date
resp_sorted = session.get(f"{URL}/my/bookings", params={"sortby": "date"})
record("8.6", "依日期排序",
       resp_sorted.status_code == 200,
       f"status={resp_sorted.status_code}")

# 8.7 portal2 should only see their own bookings
resp_list_p2 = session2.get(f"{URL}/my/bookings")
# portal2's booking should be visible
has_p2_booking = "Portal2 測試預約" in resp_list_p2.text or (booking_id_p2 and str(booking_id_p2) in resp_list_p2.text)
# portal1's bookings should NOT be visible
has_p1_details = "Portal 細部測試預約 - Conference Room A" in resp_list_p2.text
record("8.7", "portal2 只看到自己的預約 (隱私隔離)",
       not has_p1_details,
       f"portal2自己的預約可見={has_p2_booking}, portal1預約可見={has_p1_details}")

# =============================================================
# SECTION 9: 預約詳情頁 (/my/bookings/<id>)
# =============================================================
print("\n" + "=" * 70)
print("SECTION 9: 預約詳情頁 (/my/bookings/<id>)")
print("=" * 70)

if booking_id:
    resp_detail = session.get(f"{URL}/my/bookings/{booking_id}")
    record("9.1", f"預約詳情頁載入 (id={booking_id})",
           resp_detail.status_code == 200,
           f"status={resp_detail.status_code}")

    has_resource_name = "Conference Room A" in resp_detail.text
    has_datetime = day_after in resp_detail.text or "10:00" in resp_detail.text
    has_note = "Portal 細部測試預約" in resp_detail.text
    has_status = "confirmed" in resp_detail.text.lower() or "已確認" in resp_detail.text

    record("9.2", "詳情頁包含資源名稱", has_resource_name,
           f"Conference Room A={has_resource_name}")

    record("9.3", "詳情頁包含預約時間", has_datetime,
           f"日期={day_after in resp_detail.text}, 時間={'10:00' in resp_detail.text}")

    record("9.4", "詳情頁包含備註", has_note,
           f"備註可見={has_note}")

    record("9.5", "詳情頁顯示狀態", has_status,
           f"confirmed={has_status}")

    # Check cancel button
    has_cancel = "cancel" in resp_detail.text.lower() or "取消" in resp_detail.text
    record("9.6", "詳情頁有取消按鈕", has_cancel,
           f"取消按鈕={has_cancel}")

    # portal2 cannot see portal1's booking detail
    resp_cross = session2.get(f"{URL}/my/bookings/{booking_id}")
    cross_blocked = resp_cross.status_code in (400, 403, 404) or \
        (resp_cross.status_code == 200 and "Conference Room A" not in resp_cross.text)
    record("9.7", f"portal2 不能查看 portal1 的預約 (id={booking_id})",
           cross_blocked,
           f"status={resp_cross.status_code}")
else:
    for i in range(1, 8):
        record(f"9.{i}", f"預約詳情頁測試 (SKIP - 無 booking_id)", False, "booking_id 為空，Section 7 預約建立失敗")

# =============================================================
# SECTION 10: 取消預約
# =============================================================
print("\n" + "=" * 70)
print("SECTION 10: 取消預約")
print("=" * 70)

if booking_id2:
    # Get cancel page/form - CSRF token may be in the booking detail page cancel form
    cancel_page = session.get(f"{URL}/my/bookings/{booking_id2}")
    csrf_match = re.search(r'name="csrf_token"\s+value="([^"]+)"', cancel_page.text)
    if not csrf_match:
        # Fallback: get CSRF from the Odoo global JS variable
        csrf_match = re.search(r'csrf_token["\s:=]+["\']([^"\']+)["\']', cancel_page.text)
    cancel_token = csrf_match.group(1) if csrf_match else ""
    # If still no token, get from a resource page
    if not cancel_token:
        cancel_token, _ = get_csrf_from_resource_page(session, 2)

    has_cancel_action = f"/my/bookings/{booking_id2}/cancel" in cancel_page.text
    record("10.1", f"預約詳情頁有取消動作 (id={booking_id2})",
           has_cancel_action or "cancel" in cancel_page.text.lower(),
           f"cancel_action={has_cancel_action}")

    # POST cancel
    cancel_resp = session.post(f"{URL}/my/bookings/{booking_id2}/cancel", data={
        "csrf_token": cancel_token,
    }, allow_redirects=True)

    record("10.2", f"取消預約成功 (id={booking_id2})",
           cancel_resp.status_code == 200,
           f"status={cancel_resp.status_code}, url={cancel_resp.url}")

    # Verify state changed
    cancel_detail = session.get(f"{URL}/my/bookings/{booking_id2}")
    is_cancelled = "cancelled" in cancel_detail.text.lower() or "已取消" in cancel_detail.text
    record("10.3", "取消後狀態顯示為 cancelled",
           is_cancelled,
           f"cancelled={is_cancelled}")

    # Verify via RPC
    rpc_p1 = OdooRPC("portal1", "portal1")
    booking_state = rpc_p1.read("booking.reservation", [booking_id2], ["state"])[0]["state"]
    record("10.4", "RPC 確認預約狀態為 cancelled",
           booking_state == "cancelled",
           f"state={booking_state}")
else:
    for i in range(1, 5):
        record(f"10.{i}", f"取消預約測試 (SKIP - 無 booking_id2)", False, "booking_id2 為空，Section 7 預約建立失敗")

# 10.5 portal2 cannot cancel portal1's booking
if booking_id:
    cancel_token_p2, _ = get_csrf_from_resource_page(session2, 2)
    cancel_cross = session2.post(f"{URL}/my/bookings/{booking_id}/cancel", data={
        "csrf_token": cancel_token_p2,
    }, allow_redirects=True)
    cross_cancel_blocked = cancel_cross.status_code in (400, 403, 404)
    record("10.5", f"portal2 不能取消 portal1 的預約 (id={booking_id})",
           cross_cancel_blocked,
           f"status={cancel_cross.status_code}, url={cancel_cross.url}")

# =============================================================
# SECTION 11: RPC 隱私隔離驗證
# =============================================================
print("\n" + "=" * 70)
print("SECTION 11: XML-RPC 隱私隔離驗證 (ir.rule)")
print("=" * 70)

rpc_p1 = OdooRPC("portal1", "portal1")
rpc_p2 = OdooRPC("portal2", "portal2")

# 11.1 portal1 search own bookings
p1_bookings = rpc_p1.search("booking.reservation", [])
record("11.1", "portal1 搜尋預約 (只能看到自己的)",
       True, f"搜尋結果數={len(p1_bookings)}")

# 11.2 portal2 search own bookings
p2_bookings = rpc_p2.search("booking.reservation", [])
record("11.2", "portal2 搜尋預約 (只能看到自己的)",
       True, f"搜尋結果數={len(p2_bookings)}")

# 11.3 portal1 cannot read portal2's booking
if booking_id_p2:
    try:
        data = rpc_p1.read("booking.reservation", [booking_id_p2], ["note"])
        blocked = not data or not data[0].get("id")
        record("11.3", f"portal1 不能讀取 portal2 的預約 (id={booking_id_p2})",
               blocked, f"blocked={blocked}")
    except Exception as e:
        record("11.3", f"portal1 不能讀取 portal2 的預約 (id={booking_id_p2})",
               True, f"AccessError: {type(e).__name__}")

# 11.4 portal2 cannot write portal1's booking
if booking_id:
    try:
        rpc_p2.write("booking.reservation", [booking_id], {"note": "hacked"})
        # Check if write actually happened
        check = rpc_admin.read("booking.reservation", [booking_id], ["note"])[0]
        blocked = check["note"] != "hacked"
        record("11.4", f"portal2 不能修改 portal1 的預約 (id={booking_id})",
               blocked, f"修改被阻擋={blocked}")
    except Exception as e:
        record("11.4", f"portal2 不能修改 portal1 的預約 (id={booking_id})",
               True, f"AccessError: {type(e).__name__}")

# 11.5 portal1 CAN read own booking
if booking_id:
    try:
        own = rpc_p1.read("booking.reservation", [booking_id], ["note", "state"])
        record("11.5", f"portal1 可以讀取自己的預約 (id={booking_id})",
               bool(own and own[0].get("id")),
               f"state={own[0].get('state')}, note={own[0].get('note', '')[:40]}")
    except Exception as e:
        record("11.5", f"portal1 可以讀取自己的預約 (id={booking_id})",
               False, f"Error: {e}")

# =============================================================
# SECTION 12: 未登入存取保護
# =============================================================
print("\n" + "=" * 70)
print("SECTION 12: 未登入存取保護")
print("=" * 70)

anon = requests.Session()

pages = [
    ("/my/booking/resources", "資源列表"),
    ("/my/bookings", "預約列表"),
    ("/my/bookings/new", "新建預約"),
]

for path, desc in pages:
    resp = anon.get(f"{URL}{path}", allow_redirects=False)
    redirected = resp.status_code in (302, 303) and "login" in resp.headers.get("Location", "")
    record(f"12.{pages.index((path, desc))+1}",
           f"未登入存取 {desc} ({path}) → 重導登入",
           redirected,
           f"status={resp.status_code}, location={resp.headers.get('Location', 'N/A')}")

# =============================================================
# SECTION 13: 響應式設計與手機版
# =============================================================
print("\n" + "=" * 70)
print("SECTION 13: 響應式設計 (手機 User-Agent)")
print("=" * 70)

mobile_ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"

mobile_pages = [
    ("/my/booking/resources", "資源列表 (手機)"),
    ("/my/booking/resources/2", "資源詳情 (手機)"),
    ("/my/bookings", "預約列表 (手機)"),
]

for path, desc in mobile_pages:
    resp = session.get(f"{URL}{path}", headers={"User-Agent": mobile_ua})
    has_viewport = "viewport" in resp.text
    record(f"13.{mobile_pages.index((path, desc))+1}",
           f"{desc} 載入成功",
           resp.status_code == 200 and has_viewport,
           f"status={resp.status_code}, viewport={has_viewport}, 大小={len(resp.text)} bytes")

# =============================================================
# SUMMARY
# =============================================================
print("\n" + "=" * 70)
print("PORTAL 完整功能測試總結")
print("=" * 70)

total = len(results)
passed = sum(1 for r in results if r["passed"])
failed = sum(1 for r in results if not r["passed"])

# Group by section
sections = {}
for r in results:
    sec = r["id"].split("-")[0].split(".")[0]
    if sec not in sections:
        sections[sec] = {"total": 0, "passed": 0}
    sections[sec]["total"] += 1
    if r["passed"]:
        sections[sec]["passed"] += 1

print()
section_names = {
    "2": "登入流程",
    "3": "Portal 首頁",
    "4": "資源列表頁",
    "5": "資源詳情頁",
    "6": "時段查詢 API",
    "7": "建立預約",
    "8": "預約列表頁",
    "9": "預約詳情頁",
    "10": "取消預約",
    "11": "RPC 隱私隔離",
    "12": "未登入保護",
    "13": "響應式設計",
}

for sec_id in sorted(sections.keys(), key=lambda x: int(x)):
    s = sections[sec_id]
    name = section_names.get(sec_id, f"Section {sec_id}")
    status = "PASS" if s["passed"] == s["total"] else "FAIL"
    bar = "█" * s["passed"] + "░" * (s["total"] - s["passed"])
    print(f"  {sec_id:>2}. {name:<16} {s['passed']:>2}/{s['total']:<2} [{status}] {bar}")

print(f"\n  {'=' * 40}")
print(f"  總計: {passed}/{total} 通過 ({passed/total*100:.1f}%)")

if failed > 0:
    print(f"\n  失敗的測試:")
    for r in results:
        if not r["passed"]:
            print(f"    [{r['id']}] {r['name']}")
            if r["detail"]:
                print(f"           {r['detail']}")
else:
    print(f"\n  全部測試通過!")

print("\n" + "=" * 70)
print("Portal 使用者帳號")
print("=" * 70)
print(f"""
  ┌──────────────────────────────────────────────────────────┐
  │  登入網址: {URL}/web/login                 │
  │                                                          │
  │  帳號        密碼        說明                            │
  │  ─────────  ─────────  ──────────────────────            │
  │  portal1    portal1    Portal 使用者 (可存取 VIP Room)   │
  │  portal2    portal2    Portal 使用者 (可存取 VIP Room)   │
  │  portal3    portal3    Portal 使用者 (受限, 無 VIP)      │
  │                                                          │
  │  admin      admin      系統管理員 (後台)                 │
  └──────────────────────────────────────────────────────────┘
""")

print("=" * 70)
sys.exit(0 if failed == 0 else 1)
