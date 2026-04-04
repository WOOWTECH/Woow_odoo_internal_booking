{
    'name': '資源預定管理',
    'version': '18.0.1.0.0',
    'category': 'Calendar',
    'sequence': 10,
    'summary': 'Portal 使用者資源預定與管理',
    'description': '''
Odoo 18 資源預定管理模組

功能：
- 管理可預定資源（會議室、設備等）
- Portal 使用者可透過入口網站介面預定資源
- 管理員可選擇授權聯絡人來控制存取
- 自動衝突偵測，防止重複預定
- 後台行事曆視圖整合
- 支援動態屬性（Odoo 原生功能）
- 不依賴 website 模組
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
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
