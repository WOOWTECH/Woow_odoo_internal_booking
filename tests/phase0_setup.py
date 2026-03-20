#!/usr/bin/env python3
"""
Phase 0: Verify installation and create test users/data.
"""
import sys
sys.path.insert(0, '.')
from tests.odoo_rpc import OdooRPC
import json

print("=" * 60)
print("Phase 0: Setup & Verification")
print("=" * 60)

rpc = OdooRPC("admin", "admin")

# 1. Add admin to Booking Manager group
print("\n[1] Adding admin to Booking Manager group...")
manager_groups = rpc.search('res.groups', [('full_name', 'ilike', 'Booking')])
if not manager_groups:
    manager_groups = rpc.search('res.groups', [('name', 'ilike', 'manager'), ('category_id.name', 'ilike', 'book')])
if not manager_groups:
    # Search all groups
    all_groups = rpc.search_read('res.groups', [], fields=['name', 'full_name', 'category_id'])
    booking_groups = [g for g in all_groups if 'book' in (g.get('full_name') or '').lower() or 'book' in (g.get('name') or '').lower()]
    print(f"    Found booking groups: {booking_groups}")
    manager_groups = [g['id'] for g in booking_groups if 'manager' in (g.get('name') or '').lower()]
    user_groups = [g['id'] for g in booking_groups if 'user' in (g.get('name') or '').lower()]
else:
    all_booking = rpc.search_read('res.groups', [('id', 'in', manager_groups)], fields=['name', 'full_name'])
    print(f"    Found groups: {all_booking}")
    manager_groups_filtered = [g['id'] for g in all_booking if 'manager' in g['name'].lower()]
    user_groups = [g['id'] for g in all_booking if 'user' in g['name'].lower()]
    if manager_groups_filtered:
        manager_groups = manager_groups_filtered

print(f"    Manager group IDs: {manager_groups}")

# Add admin to manager group
if manager_groups:
    rpc.write('res.users', [rpc.uid], {'groups_id': [(4, gid) for gid in manager_groups]})
    print("    Admin added to Booking Manager group.")

# Re-authenticate
rpc = OdooRPC("admin", "admin")

# 2. Verify models work now
print("\n[2] Verifying models...")
for model_name in ['booking.resource.category', 'booking.resource.type', 'booking.resource.availability', 'booking.reservation']:
    try:
        count = rpc.search_count(model_name, [])
        print(f"    {model_name}: OK (records: {count})")
    except Exception as e:
        print(f"    {model_name}: ERROR - {e}")

# 3. Get all booking-related groups
print("\n[3] Finding all booking groups...")
all_groups = rpc.search_read('res.groups', [], fields=['name', 'full_name', 'category_id'])
booking_groups = [g for g in all_groups if 'book' in (g.get('full_name') or '').lower()]
portal_groups = [g for g in all_groups if g.get('full_name') and 'portal' in g['full_name'].lower()]

for g in booking_groups:
    print(f"    Booking: {g['full_name']} (ID: {g['id']})")

booking_manager_id = None
booking_user_id = None
portal_id = None

for g in booking_groups:
    if 'manager' in g['name'].lower():
        booking_manager_id = g['id']
    elif 'user' in g['name'].lower():
        booking_user_id = g['id']

for g in portal_groups:
    if g['name'] == 'Portal':
        portal_id = g['id']

if not portal_id:
    portal_search = rpc.search('res.groups', [('name', '=', 'Portal')])
    if portal_search:
        portal_id = portal_search[0]

print(f"    Manager: {booking_manager_id}, User: {booking_user_id}, Portal: {portal_id}")

# 4. Create test users
print("\n[4] Creating test users...")

def ensure_user(name, login, password, group_ids, sel_groups=None):
    existing = rpc.search('res.users', [('login', '=', login)])
    if existing:
        uid = existing[0]
        rpc.write('res.users', [uid], {'password': password, 'active': True})
        if group_ids:
            rpc.write('res.users', [uid], {'groups_id': [(4, gid) for gid in group_ids]})
        if sel_groups:
            rpc.write('res.users', [uid], sel_groups)
        print(f"    {login}: Exists (ID: {uid}), updated.")
        return uid
    else:
        vals = {
            'name': name,
            'login': login,
            'password': password,
            'email': f'{login}@test.com',
        }
        if sel_groups:
            vals.update(sel_groups)
        elif group_ids:
            vals['groups_id'] = [(6, 0, group_ids)]
        uid = rpc.create('res.users', vals)
        print(f"    {login}: Created (ID: {uid})")
        return uid

# Internal manager user
mgr_id = ensure_user('Test Manager', 'test_manager', 'test_manager',
                      [booking_manager_id] if booking_manager_id else [])

# Internal regular user
usr_id = ensure_user('Test User', 'test_user', 'test_user',
                     [booking_user_id] if booking_user_id else [])

# Portal users - use sel_groups to set portal
portal1_id = ensure_user('Portal User 1', 'portal1', 'portal1', [],
                         sel_groups={'sel_groups_1_10_11': portal_id} if portal_id else None)
portal2_id = ensure_user('Portal User 2', 'portal2', 'portal2', [],
                         sel_groups={'sel_groups_1_10_11': portal_id} if portal_id else None)
portal3_id = ensure_user('Portal User 3 (Limited)', 'portal3', 'portal3', [],
                         sel_groups={'sel_groups_1_10_11': portal_id} if portal_id else None)

# 5. Verify all users
print("\n[5] Verifying users...")
for login in ['test_manager', 'test_user', 'portal1', 'portal2', 'portal3']:
    users = rpc.search_read('res.users', [('login', '=', login)], fields=['name', 'login', 'partner_id', 'share'])
    if users:
        u = users[0]
        print(f"    {u['name']}: partner_id={u['partner_id'][0]}, portal={u.get('share', False)}")
    else:
        print(f"    {login}: NOT FOUND")

# 6. Create test resource data
print("\n[6] Creating test resources...")

# Category
cat_ids = rpc.search('booking.resource.category', [('name', '=', 'Meeting Rooms')])
if cat_ids:
    cat_id = cat_ids[0]
    print(f"    Category 'Meeting Rooms': Exists (ID: {cat_id})")
else:
    cat_id = rpc.create('booking.resource.category', {'name': 'Meeting Rooms', 'sequence': 1})
    print(f"    Category 'Meeting Rooms': Created (ID: {cat_id})")

cat2_ids = rpc.search('booking.resource.category', [('name', '=', 'Equipment')])
if cat2_ids:
    cat2_id = cat2_ids[0]
else:
    cat2_id = rpc.create('booking.resource.category', {'name': 'Equipment', 'sequence': 2})
    print(f"    Category 'Equipment': Created (ID: {cat2_id})")

# Resources
def ensure_resource(name, category_id, location, capacity, slot_duration, slot_interval, advance_days, share_type='all', partner_ids=None):
    existing = rpc.search('booking.resource.type', [('name', '=', name)])
    if existing:
        print(f"    Resource '{name}': Exists (ID: {existing[0]})")
        return existing[0]

    vals = {
        'name': name,
        'category_id': category_id,
        'location': location,
        'capacity': capacity,
        'slot_duration': slot_duration,
        'slot_interval': slot_interval,
        'advance_days': advance_days,
        'share_type': share_type,
    }
    if partner_ids:
        vals['allowed_partner_ids'] = [(6, 0, partner_ids)]

    rid = rpc.create('booking.resource.type', vals)
    print(f"    Resource '{name}': Created (ID: {rid})")
    return rid

# Get portal user partner IDs
p1_partner = rpc.search_read('res.users', [('login', '=', 'portal1')], fields=['partner_id'])[0]['partner_id'][0]
p2_partner = rpc.search_read('res.users', [('login', '=', 'portal2')], fields=['partner_id'])[0]['partner_id'][0]
p3_partner = rpc.search_read('res.users', [('login', '=', 'portal3')], fields=['partner_id'])[0]['partner_id'][0]

# Resource 1: Open to all, 1h slots back-to-back
r1 = ensure_resource('Conference Room A', cat_id, 'Building 1, Floor 3', 20,
                      1.0, 1.0, 30, share_type='all')

# Resource 2: Open to all, 30-min slots
r2 = ensure_resource('Small Meeting Room B', cat_id, 'Building 1, Floor 2', 6,
                      0.5, 0.5, 14, share_type='all')

# Resource 3: Restricted to portal1 and portal2 only
r3 = ensure_resource('VIP Room C', cat_id, 'Building 2, Floor 5', 10,
                      2.0, 2.0, 7, share_type='specific',
                      partner_ids=[p1_partner, p2_partner])

# Resource 4: Equipment - 1h slots with 30min gaps
r4 = ensure_resource('Projector', cat2_id, 'IT Department', 1,
                      1.0, 1.5, 30, share_type='all')

# Resource 5: For edge case testing - 15-min slots
r5 = ensure_resource('Phone Booth', cat_id, 'Building 1, Floor 1', 1,
                      0.25, 0.25, 3, share_type='all')

# 7. Add availability windows
print("\n[7] Setting up availability windows...")

def ensure_availability(resource_id, dayofweek, hour_from, hour_to):
    existing = rpc.search('booking.resource.availability', [
        ('resource_type_id', '=', resource_id),
        ('dayofweek', '=', dayofweek),
        ('hour_from', '=', hour_from),
        ('hour_to', '=', hour_to),
    ])
    if existing:
        return existing[0]
    return rpc.create('booking.resource.availability', {
        'resource_type_id': resource_id,
        'dayofweek': dayofweek,
        'hour_from': hour_from,
        'hour_to': hour_to,
    })

# Monday to Friday, 9:00 - 18:00 for main rooms
for resource_id in [r1, r2, r3, r4, r5]:
    for day in ['0', '1', '2', '3', '4']:  # Mon-Fri
        ensure_availability(resource_id, day, 9.0, 18.0)

# Saturday availability for Conference Room A
ensure_availability(r1, '5', 10.0, 14.0)  # Saturday 10:00-14:00

avail_count = rpc.search_count('booking.resource.availability', [])
print(f"    Total availability windows: {avail_count}")

# 8. Summary
print("\n" + "=" * 60)
print("Phase 0 Complete - Summary")
print("=" * 60)

results = {
    'users': {
        'admin': {'id': rpc.uid, 'role': 'Booking Manager (admin)'},
        'test_manager': {'id': mgr_id, 'role': 'Booking Manager'},
        'test_user': {'id': usr_id, 'role': 'Booking User'},
        'portal1': {'id': portal1_id, 'role': 'Portal User', 'partner_id': p1_partner},
        'portal2': {'id': portal2_id, 'role': 'Portal User', 'partner_id': p2_partner},
        'portal3': {'id': portal3_id, 'role': 'Portal User (Limited)', 'partner_id': p3_partner},
    },
    'resources': {
        'Conference Room A': {'id': r1, 'share': 'all', 'slot': '1h'},
        'Small Meeting Room B': {'id': r2, 'share': 'all', 'slot': '30min'},
        'VIP Room C': {'id': r3, 'share': 'specific', 'slot': '2h'},
        'Projector': {'id': r4, 'share': 'all', 'slot': '1h'},
        'Phone Booth': {'id': r5, 'share': 'all', 'slot': '15min'},
    },
    'categories': {
        'Meeting Rooms': cat_id,
        'Equipment': cat2_id,
    },
    'groups': {
        'booking_manager': booking_manager_id,
        'booking_user': booking_user_id,
        'portal': portal_id,
    }
}

print(json.dumps(results, indent=2, ensure_ascii=False))

# Save for other test scripts
with open('tests/test_config.json', 'w') as f:
    json.dump(results, f, indent=2, ensure_ascii=False)
print("\nConfig saved to tests/test_config.json")
