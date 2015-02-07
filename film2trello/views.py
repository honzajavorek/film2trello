# -*- coding: utf-8 -*-


import re

from flask import render_template, url_for, request, redirect

from . import app, trello
from .csfd import scrape_film
from .forms import SettingsForm
from .deferred import call_after_request_callbacks


@app.route('/')
def index():
    """Renders the home page."""
    return render_template(
        'index.html',
        bookmarklet=render_bookmarklet(
            'bookmarklet.js',
            url=url_for('add', _external=True)
        )
    )


def render_bookmarklet(*args, **kwargs):
    """Renders code for bookmarklet."""
    js_code = render_template(*args, **kwargs)
    return re.sub(r'\s+', ' ', js_code)  # one line, compressed


@app.route('/add', methods=['POST'])
def add():
    """Entry point for adding of the film."""
    url = request.form.get('url')

    if not trello.get_auth():
        return trello.authorize(url_for('auth', url=url))
    return handle_settings(url)


@app.route('/auth')
def auth():
    """Handles auth and adds the film."""
    url = request.args.get('url')

    if not trello.authorized_successfuly():
        return redirect(url_for('failure', reason='denied', film_url=url))
    return handle_settings(url)


def handle_settings(url):
    if not trello.get_board_id():
        return redirect(url_for('settings', url=url))
    return redirect(url_for('create_card', url=url))


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    url = request.args.get('url')
    form = SettingsForm()

    if form.validate_on_submit():
        trello.set_board_url(form.data['trello_board_url'])
        return redirect(url_for('create_card', url=url))

    action_url = url_for('settings', url=url)
    return render_template('settings.html', form=form, action_url=action_url)


@app.route('/create-card')
def create_card():
    url = request.args.get('url')
    board_id = trello.get_board_id()

    film = scrape_film(url)
    card_url = trello.create_card(board_id, film)

    next_url = url_for('success', film_url=film['url'], card_url=card_url)
    return redirect(next_url)


@app.route('/success')
def success():
    return render_template('success.html',
                           film_url=request.args.get('film_url'),
                           card_url=request.args.get('card_url'))


@app.route('/failure')
def failure():
    return render_template('failure.html',
                           film_url=request.args.get('film_url'),
                           reason=request.args.get('reason'))


app.after_request(call_after_request_callbacks)
