import os
import re

from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash)
from lxml import html
import requests

from . import csfd


USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) '
              'Gecko/20100101 Firefox/72.0')
TRELLO_KEY = os.getenv('TRELLO_KEY')
TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')
TRELLO_BOARD = os.getenv('TRELLO_BOARD')


app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', os.urandom(16))


@app.route('/', methods=['GET', 'POST'])
def index():
    return post() if request.method == 'POST' else get()


def get():
    trello_board_url = f'https://trello.com/b/{TRELLO_BOARD}/'
    return render_template('index.html',
                           username=session.get('username'),
                           trello_board_url=trello_board_url)


def post():
    username = request.form.get('username')
    username = None if username in ('None', '') else username
    film_url = request.form.get('film_url', '')
    try:
        film_url = csfd.normalize_url(film_url)

        res = requests.get(film_url, headers={'User-Agent': USER_AGENT})
        res.raise_for_status()
        html_tree = html.fromstring(res.content)

        film = dict(url=res.url, title=csfd.parse_title(html_tree),
                    poster_url=csfd.parse_poster_url(html_tree))
        card_url = create_card(username, film)

        session['username'] = username

        bookmarklet = render_bookmarklet('bookmarklet.js',
                                         url=url_for('index', _external=True),
                                         username=username)
        return render_template('submission.html', username=username, film=film,
                               card_url=card_url, bookmarklet=bookmarklet)
    except csfd.InvalidURLError:
        flash(f"Not a valid CSFD.cz film URL: '{film_url}'")
        return redirect(url_for('index'))
    except requests.RequestException as exc:
        flash(str(exc))
        return redirect(url_for('index'))


def create_card(username, film):
    cards = request_trello('get', f'/boards/{TRELLO_BOARD}/cards',
                           params=dict(filter='open'))

    card_id = None
    for card in cards:
        if film['title'] in card['name'] or film['url'] in card['desc']:
            card_id = card['id']
            break

    if not card_id:
        lists = request_trello('get', f'/boards/{TRELLO_BOARD}/lists')

        card = request_trello('post', '/cards', data={
            'name': film['title'],
            'idList': lists[0]['id'],
            'desc': film['url'],
        })
        card_id = card['id']

    members = request_trello('get', f'/cards/{card_id}/members')
    if username not in [member['username'] for member in members]:
        user = request_trello('get', f'/members/{username}')
        request_trello('post', f'/cards/{card_id}/members', data={
            'value': user['id']
        })

    attachments = request_trello('get', f'/cards/{card_id}/attachments')
    if not len(attachments):
        request_trello('post', f'/cards/{card_id}/attachments', data={
            'url': film['poster_url']
        })

    return f'https://trello.com/c/{card_id}'


def request_trello(method, path, params=None, data=None):
    params = params or {}
    if not params.get('token'):
        params['token'] = TRELLO_TOKEN
    if not params.get('key'):
        params['key'] = TRELLO_KEY

    url = 'https://trello.com/1/' + path.lstrip('/')

    res = requests.request(method, url, params=params, data=data)
    res.raise_for_status()
    return res.json()


def render_bookmarklet(*args, **kwargs):
    js_code = render_template(*args, **kwargs)
    return re.sub(r'\s+', ' ', js_code)  # one line, compressed
