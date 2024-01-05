import os
import re
import sys
from io import BytesIO
import json
from pathlib import Path

from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    send_from_directory,
)
from lxml import html
import requests
from PIL import Image

from ...film2trello import csfd
from ...film2trello import trello


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.14; rv:72.0) "
    "Gecko/20100101 Firefox/72.0"
)
TRELLO_TOKEN = os.getenv("TRELLO_TOKEN")
TRELLO_KEY = os.getenv("TRELLO_KEY")
TRELLO_BOARD = os.getenv("TRELLO_BOARD")

LARGE_RESPONSE_MB = 10
THUMBNAIL_SIZE = (500, 500)

CSFD_URL_RE = re.compile(r'https?://(www\.)?csfd\.cz/[^"]+')


def post():
    username = parse_username(request.form.get("username"))
    film_url = request.form.get("film_url", "")
    try:
        film_url = get_film_url(film_url)
        film = get_film(film_url)
        card_url = create_card(username, film)
    except csfd.InvalidURLError:
        flash(f"Not a valid film URL: '{film_url}'")
        return redirect(url_for("index"))
    except trello.InvalidUsernameError:
        flash(f"User '{username}' is not allowed to the board")
        return redirect(url_for("index"))
    except requests.RequestException as exc:
        flash(sanitize_exception(str(exc)))
        print(
            f'{exc} - {exc.response.text if exc.response else "[no response]"}',
            file=sys.stderr,
        )
        return redirect(url_for("index"))


def create_card(username, film):
    api = trello.create_session(TRELLO_TOKEN, TRELLO_KEY)

    members = api.get(f"/boards/{TRELLO_BOARD}/members")
    if trello.not_in_members(username, members):
        raise trello.InvalidUsernameError()

    lists = api.get(f"/boards/{TRELLO_BOARD}/lists")
    inbox_list_id = trello.get_inbox_id(lists)
    archive_list_id = trello.get_archive_id(lists)

    inbox_cards = api.get(f"/lists/{inbox_list_id}/cards")
    archive_cards = api.get(f"/lists/{archive_list_id}/cards")
    cards = inbox_cards + archive_cards

    card_id = trello.card_exists(cards, film)
    if card_id:
        api.put(
            f"/cards/{card_id}/", data=trello.prepare_updated_card_data(inbox_list_id)
        )
    else:
        card_data = trello.prepare_card_data(inbox_list_id, film)
        card = api.post("/cards", data=card_data)
        card_id = card["id"]

    update_members(api, card_id, username)
    update_labels(api, card_id, film)
    update_attachments(api, card_id, film)
    return f"https://trello.com/c/{card_id}"


def update_members(api, card_id, username):
    existing_members = api.get(f"/cards/{card_id}/members")
    if trello.not_in_members(username, existing_members):
        user = api.get(f"/members/{username}")
        api.post(f"/cards/{card_id}/members", data=dict(value=user["id"]))


def update_labels(api, card_id, film):
    existing_labels = api.get(f"/cards/{card_id}/labels")
    labels = list(trello.prepare_duration_labels(film["durations"]))
    if film.get("kvifftv_url"):
        labels.append(trello.KVIFFTV_LABEL)
    labels = trello.get_missing_labels(existing_labels, labels)
    for label in labels:
        try:
            api.post(f"/cards/{card_id}/labels", params=label)
        except requests.RequestException as e:
            if "label is already on the card" not in e.response.text:
                raise e


def update_attachments(api, card_id, film):
    existing_attachments = api.get(f"/cards/{card_id}/attachments")
    urls = [film["url"]]
    if film.get("kvifftv_url"):
        urls.append(film["kvifftv_url"])
    urls = trello.get_missing_attached_urls(existing_attachments, urls)
    for url in urls:
        api.post(f"/cards/{card_id}/attachments", data=dict(url=url))

    if not trello.has_poster(existing_attachments) and film["poster_url"]:
        with requests.get(film["poster_url"], stream=True) as response:
            api.post(
                f"/cards/{card_id}/attachments",
                files=dict(file=create_thumbnail(response)),
            )


def create_thumbnail(response):
    image = Image.open(response.raw).convert("RGB")
    image.thumbnail(THUMBNAIL_SIZE)
    image_file = BytesIO()
    image.save(image_file, "JPEG")
    image_file.seek(0)
    return ("poster.jpg", image_file, "image/jpeg")
