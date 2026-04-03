from odoo import fields, models


class BookingResourceCategory(models.Model):
    """
    Category for booking resources.
    Holds the properties definition that can be shared across resources.
    """
    _name = 'booking.resource.category'
    _description = '預定資源分類'
    _order = 'sequence, name'

    name = fields.Char(
        string='名稱',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        string='排序',
        default=10,
    )
    active = fields.Boolean(
        string='啟用',
        default=True,
    )

    # 此分類的屬性定義
    resource_properties_definition = fields.PropertiesDefinition(
        string='資源屬性',
    )

    # 關聯資源
    resource_ids = fields.One2many(
        'booking.resource.type',
        'category_id',
        string='資源',
    )
    resource_count = fields.Integer(
        string='資源數量',
        compute='_compute_resource_count',
    )

    def _compute_resource_count(self):
        for category in self:
            category.resource_count = len(category.resource_ids)
