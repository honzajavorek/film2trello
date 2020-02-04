import os
import re

from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash)
from lxml import html
import requests

from . import csfd
from . import trello


USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) '
              'Gecko/20100101 Firefox/72.0')
TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')
TRELLO_KEY = os.getenv('TRELLO_KEY')
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
    username = parse_username(request.form.get('username'))
    film_url = request.form.get('film_url', '')
    try:
        film_url = csfd.normalize_url(film_url)

        res = requests.get(film_url, headers={'User-Agent': USER_AGENT})
        res.raise_for_status()
        html_tree = html.fromstring(res.content)

        film = dict(url=res.url, title=csfd.parse_title(html_tree),
                    poster_url=csfd.parse_poster_url(html_tree),
                    durations=csfd.parse_durations(html_tree))
        card_url = create_card(username, film)

        session['username'] = username

        bookmarklet = render_bookmarklet('bookmarklet.js',
                                         url=url_for('index', _external=True),
                                         username=username)
        return render_template('submission.html', username=username, film=film,
                               card_url=card_url, bookmarklet=bookmarklet,
                               trello_board_url=TRELLO_BOARD)
    except csfd.InvalidURLError:
        flash(f"Not a valid CSFD.cz film URL: '{film_url}'")
        return redirect(url_for('index'))
    except trello.InvalidUsernameError:
        flash(f"User '{username}' is not allowed to the board")
        return redirect(url_for('index'))
    except requests.RequestException as exc:
        flash(sanitize_exception(str(exc)))
        return redirect(url_for('index'))


def create_card(username, film):
    api = trello.create_session(TRELLO_TOKEN, TRELLO_KEY)

    members = api.get(f'/boards/{TRELLO_BOARD}/members')
    if trello.not_in_members(username, members):
        raise trello.InvalidUsernameError()

    cards = api.get(f'/boards/{TRELLO_BOARD}/cards',
                    params=dict(filter='open'))

    card_id = trello.card_exists(cards, film)
    if not card_id:
        lists = api.get(f'/boards/{TRELLO_BOARD}/lists')
        inbox_list_id = trello.get_inbox_id(lists)
        card_data = trello.prepare_card_data(inbox_list_id, film)
        card = api.post('/cards', data=card_data)
        card_id = card['id']

    members = api.get(f'/cards/{card_id}/members')
    if trello.not_in_members(username, members):
        user = api.get(f'/members/{username}')
        api.post(f'/cards/{card_id}/members', data=dict(value=user['id']))

    labels = api.get(f'/cards/{card_id}/labels')
    if not labels:
        for label in trello.prepare_labels(film['durations']):
            api.post(f'/cards/{card_id}/labels', params=label)

    attachments = api.get(f'/cards/{card_id}/attachments')
    if not len(attachments):
        api.post(f'/cards/{card_id}/attachments',
                 data=dict(url=film['poster_url']))

    return f'https://trello.com/c/{card_id}'


def render_bookmarklet(*args, **kwargs):
    return compress_javascript(render_template(*args, **kwargs))


def compress_javascript(code):
    """Compress JS to just one line"""
    return re.sub(r'\s+', ' ', code)


def parse_username(username):
    return None if username in ('None', '') else username


def sanitize_exception(text):
    return text \
        .replace(TRELLO_KEY, '<TRELLO_KEY>') \
        .replace(TRELLO_TOKEN, '<TRELLO_TOKEN>')
