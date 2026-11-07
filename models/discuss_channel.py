from odoo import models
from odoo.exceptions import UserError
from odoo.tools.translate import _


class DiscussChannel(models.Model):
    _inherit = 'discuss.channel'

    def _create_sub_channel(self, from_message_id=None, name=None):
        """No threads in booking discussions.

        Booking discussions are members-only 'group' conversations. A core
        sub-channel is always of type 'channel' and inherits its visibility
        from the parent's group_public_id, which is empty on a group: the
        thread would be readable and joinable by every portal user.
        """
        if self.channel_type != 'channel' and self.env['booking.reservation'].sudo().search_count(
                [('channel_id', '=', self.id)], limit=1):
            raise UserError(_('Threads are not available in booking discussions.'))
        return super()._create_sub_channel(from_message_id=from_message_id, name=name)
