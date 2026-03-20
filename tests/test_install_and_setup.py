#!/usr/bin/env python3
"""
Phase 0: Install module and setup test accounts
"""
import xmlrpc.client
import json
import sys

URL = "http://localhost:9071"
DB = "odoocalendar"
ADMIN_USER = "admin"
ADMIN_PASS = "admin"

common = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/common")
uid = common.authenticate(DB, ADMIN_USER, ADMIN_PASS, {})
models = xmlrpc.client.ServerProxy(f"{URL}/xmlrpc/2/object")

def call(model, method, *args, **kwargs):
    return models.execute_kw(DB, uid, ADMIN_PASS, model, method, list(args), kwargs or {})

def read(model, ids, fields=None):
    """Properly call read with fields as keyword argument."""
    return models.execute_kw(DB, uid, ADMIN_PASS, model, 'read', [ids], {'fields': fields or []})

print("=" * 60)
print("Phase 0: Module Installation & Setup")
print("=" * 60)

# Step 1: Update module list
print("\n[1] Updating module list...")
call('ir.module.module', 'update_list')
print("    Module list updated.")

# Step 2: Search for the booking module
print("\n[2] Searching for odoo_booking_reservation module...")
mod_ids = call('ir.module.module', 'search', [('name', '=', 'odoo_booking_reservation')])
if not mod_ids:
    print("    ERROR: Module not found! Check addons path.")
    sys.exit(1)

mod_info = read('ir.module.module', mod_ids, ['name', 'state', 'installed_version'])
print(f"    Found: {mod_info[0]['name']}, State: {mod_info[0]['state']}, Version: {mod_info[0].get('installed_version', 'N/A')}")

# Step 3: Install module if not installed
if mod_info[0]['state'] != 'installed':
    print("\n[3] Installing module...")
    call('ir.module.module', 'button_immediate_install', mod_ids)
    print("    Module installed successfully!")
else:
    print("\n[3] Module already installed, upgrading...")
    call('ir.module.module', 'button_immediate_upgrade', mod_ids)
    print("    Module upgraded.")

# Re-authenticate after install (session may change)
uid = common.authenticate(DB, ADMIN_USER, ADMIN_PASS, {})

# Step 4: Verify models exist
print("\n[4] Verifying models exist...")
expected_models = [
    'booking.resource.category',
    'booking.resource.type',
    'booking.resource.availability',
    'booking.reservation',
]
for model_name in expected_models:
    try:
        count = call(model_name, 'search_count', [])
        print(f"    {model_name}: OK (records: {count})")
    except Exception as e:
        print(f"    {model_name}: ERROR - {e}")

# Step 5: Verify security groups exist
print("\n[5] Verifying security groups...")
groups = call('res.groups', 'search_read',
    [('category_id.name', 'ilike', 'Booking')],
    {'fields': ['name', 'full_name', 'users']})
if groups:
    for g in groups:
        print(f"    Group: {g['full_name']} (users: {len(g['users'])})")
else:
    # Try searching differently
    groups = call('res.groups', 'search_read',
        [('name', 'ilike', 'booking')],
        {'fields': ['name', 'full_name', 'users']})
    for g in groups:
        print(f"    Group: {g['full_name']} (users: {len(g['users'])})")

# Step 6: Create test users
print("\n[6] Creating test users...")

# Get booking groups
booking_user_group = call('res.groups', 'search', [('name', 'ilike', 'user'), ('category_id.name', 'ilike', 'booking')])
booking_manager_group = call('res.groups', 'search', [('name', 'ilike', 'manager'), ('category_id.name', 'ilike', 'booking')])
portal_group = call('res.groups', 'search', [('name', '=', 'Portal')])

if not booking_user_group:
    booking_user_group = call('res.groups', 'search', [('name', 'ilike', 'user'), ('name', 'ilike', 'booking')])
if not booking_manager_group:
    booking_manager_group = call('res.groups', 'search', [('name', 'ilike', 'manager'), ('name', 'ilike', 'booking')])

print(f"    Booking User Group IDs: {booking_user_group}")
print(f"    Booking Manager Group IDs: {booking_manager_group}")
print(f"    Portal Group IDs: {portal_group}")

test_users = {
    'test_manager': {
        'name': 'Test Manager',
        'login': 'test_manager',
        'password': 'test_manager',
        'email': 'test_manager@test.com',
        'groups': booking_manager_group,
        'type': 'internal',
    },
    'test_user': {
        'name': 'Test User',
        'login': 'test_user',
        'password': 'test_user',
        'email': 'test_user@test.com',
        'groups': booking_user_group,
        'type': 'internal',
    },
    'portal_user1': {
        'name': 'Portal User 1',
        'login': 'portal1',
        'password': 'portal1',
        'email': 'portal1@test.com',
        'groups': portal_group,
        'type': 'portal',
    },
    'portal_user2': {
        'name': 'Portal User 2',
        'login': 'portal2',
        'password': 'portal2',
        'email': 'portal2@test.com',
        'groups': portal_group,
        'type': 'portal',
    },
}

created_users = {}
for key, user_data in test_users.items():
    existing = call('res.users', 'search', [('login', '=', user_data['login'])])
    if existing:
        print(f"    {key}: Already exists (ID: {existing[0]})")
        created_users[key] = existing[0]
        # Update password
        try:
            call('res.users', 'write', existing, {'password': user_data['password']})
        except:
            pass
    else:
        try:
            vals = {
                'name': user_data['name'],
                'login': user_data['login'],
                'password': user_data['password'],
                'email': user_data['email'],
            }
            if user_data['groups']:
                vals['groups_id'] = [(6, 0, user_data['groups'])]

            new_id = call('res.users', 'create', [vals])
            print(f"    {key}: Created (ID: {new_id})")
            created_users[key] = new_id
        except Exception as e:
            print(f"    {key}: ERROR creating - {e}")

# Step 7: Verify portal users
print("\n[7] Verifying test users...")
for key, user_id in created_users.items():
    user_info = read('res.users', [user_id], ['name', 'login', 'groups_id', 'partner_id'])
    if user_info:
        u = user_info[0]
        print(f"    {u['name']} (login: {u['login']}, partner_id: {u['partner_id'][0]}, groups: {len(u['groups_id'])})")

# Step 8: Check menus and actions
print("\n[8] Verifying menus and actions...")
menus = call('ir.ui.menu', 'search_read',
    [('name', 'ilike', 'booking')],
    {'fields': ['name', 'complete_name', 'action']})
for m in menus:
    print(f"    Menu: {m['complete_name']} -> {m.get('action', 'N/A')}")

# Also check for Resource Bookings menu
menus2 = call('ir.ui.menu', 'search_read',
    [('name', 'ilike', 'resource')],
    {'fields': ['name', 'complete_name']})
for m in menus2:
    if 'booking' in m.get('complete_name', '').lower() or 'resource' in m.get('complete_name', '').lower():
        print(f"    Menu: {m['complete_name']}")

print("\n" + "=" * 60)
print("Phase 0 Complete!")
print("=" * 60)

# Save results for later reference
results = {
    'module_installed': True,
    'models_verified': True,
    'test_users': {k: v for k, v in created_users.items()},
    'groups': {
        'booking_user': booking_user_group,
        'booking_manager': booking_manager_group,
        'portal': portal_group,
    }
}
print(f"\nResults: {json.dumps(results, indent=2)}")
