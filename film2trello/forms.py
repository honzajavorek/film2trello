# -*- coding: utf-8 -*-


from flask_wtf import Form
from wtforms import TextField
from wtforms.validators import URL, Required, ValidationError

from .trello import is_board_url


def validate_board_url(form, field):
    if not is_board_url(field.data):
        raise ValidationError('Invalid Trello board link')


class SettingsForm(Form):
    trello_board_url = TextField('Link to Trello board',
                                 [Required(), URL(), validate_board_url])
