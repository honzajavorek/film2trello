# -*- coding: utf-8 -*-


import os


SECRET_KEY = os.environ.get('SECRET_KEY', 'dummy secret key')

TRELLO_KEY = os.environ.get('TRELLO_KEY')
TRELLO_SECRET = os.environ.get('TRELLO_SECRET')

REDIS_URL = os.environ.get(
    'REDIS_URL',
    os.environ.get('REDISTOGO_URL', 'redis://localhost:6379')
)
