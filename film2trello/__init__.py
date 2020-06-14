import os
import re
import sys
from io import BytesIO
import json
from pathlib import Path

from flask import (Flask, render_template, request, redirect, url_for, session,
                   flash)
from lxml import html
import requests
from PIL import Image

from . import csfd
from . import trello


USER_AGENT = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) '
              'Gecko/20100101 Firefox/72.0')
TRELLO_TOKEN = os.getenv('TRELLO_TOKEN')
TRELLO_KEY = os.getenv('TRELLO_KEY')
TRELLO_BOARD = os.getenv('TRELLO_BOARD')

LARGE_RESPONSE_MB = 10
THUMBNAIL_SIZE = (500, 500)

AEROVOD_DATA_PATH = Path(__file__).parent / 'aerovod.json'
try:
    AEROVOD_DATA = [
        (
            dict(url=item['url'], csfd_url=csfd.normalize_url(item['csfd_url']))
            if item['csfd_url']
            else dict(url=item['url'], csfd_url=None)
        )
        for item in json.loads(AEROVOD_DATA_PATH.read_text())
    ]
except IOError:
    print('Could not load Aerovod data', file=sys.stderr)
    AEROVOD_DATA = []


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
        film = get_film(film_url)
        aerovod_film = get_aerovod_film(film_url)
        card_url = create_card(username, film, aerovod_film=aerovod_film)

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
        print(f'{exc} - {exc.response.text}', file=sys.stderr)
        return redirect(url_for('index'))


def get_film(film_url):
    res = requests.get(film_url, headers={'User-Agent': USER_AGENT})
    res.raise_for_status()
    html_tree = html.fromstring(res.content)

    return dict(url=res.url, title=csfd.parse_title(html_tree),
                poster_url=csfd.parse_poster_url(html_tree),
                durations=csfd.parse_durations(html_tree))


def get_aerovod_film(film_url):
    for aerovod_film in AEROVOD_DATA:
        if aerovod_film['csfd_url'] == film_url:
            return aerovod_film
    return None


def create_card(username, film, aerovod_film=None):
    api = trello.create_session(TRELLO_TOKEN, TRELLO_KEY)

    members = api.get(f'/boards/{TRELLO_BOARD}/members')
    if trello.not_in_members(username, members):
        raise trello.InvalidUsernameError()

    cards = api.get(f'/boards/{TRELLO_BOARD}/cards',
                    params=dict(filter='open'))

    card_id = trello.card_exists(cards, film)
    if card_id:
        api.put(f'/cards/{card_id}/', data=trello.prepare_updated_card_data())
    else:
        lists = api.get(f'/boards/{TRELLO_BOARD}/lists')
        inbox_list_id = trello.get_inbox_id(lists)
        card_data = trello.prepare_card_data(inbox_list_id, film)
        card = api.post('/cards', data=card_data)
        card_id = card['id']

    update_members(api, card_id, username)
    update_labels(api, card_id, film, aerovod_film=aerovod_film)
    update_attachments(api, card_id, film, aerovod_film=aerovod_film)
    return f'https://trello.com/c/{card_id}'


def update_members(api, card_id, username):
    existing_members = api.get(f'/cards/{card_id}/members')
    if trello.not_in_members(username, existing_members):
        user = api.get(f'/members/{username}')
        api.post(f'/cards/{card_id}/members', data=dict(value=user['id']))


def update_labels(api, card_id, film, aerovod_film=None):
    existing_labels = api.get(f'/cards/{card_id}/labels')
    labels = list(trello.prepare_duration_labels(film['durations']))
    if aerovod_film:
        labels.append(trello.AEROVOD_LABEL)
    labels = trello.get_missing_labels(existing_labels, labels)
    for label in labels:
        try:
            api.post(f'/cards/{card_id}/labels', params=label)
        except requests.RequestException as e:
            if 'label is already on the card' not in e.response.text:
                raise e


def update_attachments(api, card_id, film, aerovod_film=None):
    existing_attachments = api.get(f'/cards/{card_id}/attachments')
    urls = [film['url']]
    if aerovod_film:
        urls.append(aerovod_film['url'])
    urls = trello.get_missing_attached_urls(existing_attachments, urls)
    for url in urls:
        api.post(f'/cards/{card_id}/attachments', data=dict(url=url))

    if not trello.has_poster(existing_attachments):
        with requests.get(film['poster_url'], stream=True) as response:
            api.post(f'/cards/{card_id}/attachments',
                     files=dict(file=create_thumbnail(response)))


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


def create_thumbnail(response):
    image = Image.open(response.raw).convert('RGB')
    image.thumbnail(THUMBNAIL_SIZE)
    image_file = BytesIO()
    image.save(image_file, 'JPEG')
    image_file.seek(0)
    return ('poster.jpg', image_file, 'image/jpeg')
