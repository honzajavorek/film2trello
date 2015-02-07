# -*- coding: utf-8 -*-


from flask import Flask


app = Flask(__name__)
app.config.from_object('film2trello.config')


from . import views  # NOQA
