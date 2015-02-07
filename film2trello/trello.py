# -*- coding: utf-8 -*-


from __future__ import absolute_import

import re
import json

import requests
from flask import request, g
from redis import StrictRedis as Redis
from flask_oauthlib.client import OAuth

from . import app
from .deferred import after_this_request


_board_url_re = re.compile(r'^https?://trello\.com/b/(?P<id>\w+)/?(.*)')


oauth = OAuth()
api = oauth.remote_app(
    'Trello',
    base_url='https://trello.com/1/',
    request_token_url='https://trello.com/1/OAuthGetRequestToken',
    access_token_url='https://trello.com/1/OAuthGetAccessToken',
    authorize_url='https://trello.com/1/OAuthAuthorizeToken',
    consumer_key=app.config['TRELLO_KEY'],
    consumer_secret=app.config['TRELLO_SECRET']
)
redis = Redis.from_url(app.config['REDIS_URL'])


@api.tokengetter
def get_auth():
    if not hasattr(g, 'auth') or not g.auth:
        g.auth = None
        username = get_username()
        if username:
            auth = redis.get('{}_auth'.format(username))
            if auth:
                g.auth = json.loads(auth)
    return g.auth


def get_username(token=None):
    if not hasattr(g, 'username') or not g.username:
        username = request.cookies.get('trello_username')
        if not username and token:
            me = _request('get', '/members/me', params={'token': token})
            username = me['username']

            @after_this_request
            def remember_username(res):
                res.set_cookie('trello_username', username)

        g.username = username
    return g.username


def is_board_url(board_url):
    return bool(_board_url_re.match(board_url))


def get_board_id():
    if not hasattr(g, 'board_id') or not g.board:
        g.board_id = request.cookies.get('trello_board_id')
    return g.board_id


def set_board_url(board_url):
    match = _board_url_re.match(board_url)
    set_board_id(match.groupdict()['id'])


def set_board_id(board_id):
    @after_this_request
    def remember_board_id(res):
        res.set_cookie('trello_board_id', board_id)
    g.board_id = board_id


def authorize(callback):
    return api.authorize(
        callback=callback,
        name='film2trello',
        scope='read,write',
        expiration='never',
    )


def authorized_successfuly():
    auth = api.authorized_response()

    if isinstance(auth, Exception):
        raise auth

    if auth is None:
        return False

    username = get_username(token=auth['oauth_token'])
    redis.set('{}_auth'.format(username), json.dumps(auth))
    return True


def create_card(board_id, film):
    cards = _request('get', '/boards/{}/cards'.format(board_id),
                     params={'filter': 'open'})

    card_id = None
    for card in cards:
        if film['title'] in card['name'] or film['url'] in card['desc']:
            card_id = card['id']
            break

    if not card_id:
        lists = _request('get', '/boards/{}/lists'.format(board_id))

        card = _request('post', '/cards', data={
            'name': film['title'],
            'idList': lists[0]['id'],
            'desc': film['url'],
        })
        card_id = card['id']

    members = _request('get', '/cards/{}/members'.format(card_id))
    if get_username() not in [member['username'] for member in members]:
        me = _request('get', '/members/me')
        _request('post', '/cards/{}/members'.format(card_id), data={
            'value': me['id']
        })

    attachments = _request('get', '/cards/{}/attachments'.format(card_id))
    if not len(attachments):
        _request('post', '/cards/{}/attachments'.format(card_id), data={
            'url': film['poster_url']
        })

    return 'https://trello.com/c/{}'.format(card_id)


def _request(method, path, params=None, data=None):
    params = params or {}
    if not params.get('token'):
        params['token'] = get_auth()['oauth_token']

    url = 'https://trello.com/1/' + path.lstrip('/')
    params = dict(key=app.config['TRELLO_KEY'], **params)

    res = requests.request(method, url, params=params, data=data)
    res.raise_for_status()
    return json.loads(res.content)
