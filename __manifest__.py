{
    'name': 'Booking Reservation',
    'version': '18.0.1.0.0',
    'category': 'Calendar',
    'sequence': 10,
    'summary': 'Resource Booking and Reservation Management for Portal Users',
    'description': '''
Odoo 18 Resource Booking & Reservation Module

Features:
- Manage bookable resources (meeting rooms, equipment, etc.)
- Portal users can book resources from Portal interface
- Administrators control access by selecting authorized contacts
- Automatic conflict detection prevents double booking
- Calendar view integration in backend
- Dynamic attributes support (native Odoo feature)
- Does not depend on website module
    ''',
    'author': 'WOOWTECH',
    'website': 'https://woowtech.com',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'mail',
        'calendar',
        'portal',
    ],
    'data': [
        # Security
        'security/booking_groups.xml',
        'security/ir.model.access.csv',
        'security/booking_rules.xml',
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
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
