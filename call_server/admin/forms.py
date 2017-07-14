from flask_wtf import FlaskForm
from flask_babel import gettext as _
from wtforms import StringField, SubmitField
from wtforms_components import PhoneNumberField, TimeField
from wtforms.validators import Optional, IPAddress


class BlocklistForm(FlaskForm):
    phone_number = PhoneNumberField(_('Phone Number'), [Optional()])
    phone_hash = StringField(_('Phone Hash'), validators=[Optional()])
    ip_address = StringField(_('IP Address'), validators=[Optional(), IPAddress()])
    expires = TimeField(_('Expiration'), [Optional()])
    submit = SubmitField(_('Next'))

    def validate(self):
        if not super(BlocklistForm, self).validate():
            return False
        if not self.phone_number.data  and not self.phone_hash.data and not self.ip_address.data:
            msg = 'At least one of Phone Number, Phone hash, or IP Address must be set'
            self.phone_number.errors.append(msg)
            self.phone_hash.errors.append(msg)
            self.ip_address.errors.append(msg)
            return False
        return True