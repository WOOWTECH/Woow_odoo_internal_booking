{
    'name': 'Resource Booking Management',
    'version': '18.0.1.0.0',
    'category': 'Calendar',
    'sequence': 10,
    'summary': 'Resource booking and management for Portal users',
    'description': '''
Odoo 18 Resource Booking Management Module

Features:
- Manage bookable resources (meeting rooms, equipment, etc.)
- Portal users can book resources through the portal interface
- Administrators can control access by selecting authorized contacts
- Automatic conflict detection to prevent double bookings
- Backend calendar view integration
- Category tagging with color support
- Dynamic properties support (Odoo 18 native feature)
- Does not depend on the website module
    ''',
    'author': 'WOOWTECH',
    'website': 'https://woowtech.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'calendar',
        'portal',
        'cs_portal_discuss',
    ],
    'data': [
        # Security
        'security/booking_groups.xml',
        'security/ir.model.access.csv',
        'security/booking_rules.xml',
        # Data
        'data/mail_template_data.xml',
        # Views
        'views/booking_resource_category_views.xml',
        'views/booking_resource_type_views.xml',
        'views/booking_reservation_views.xml',
        'views/booking_menus.xml',
        # Portal
        'views/portal_templates.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'odoo_booking_reservation/static/src/views/**/*',
        ],
        'web.assets_frontend': [
            'odoo_booking_reservation/static/src/css/portal.css',
            'odoo_booking_reservation/static/src/js/portal_attendee.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
