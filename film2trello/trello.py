import asyncio
from io import BytesIO
import itertools
import math
from typing import Literal

from PIL import Image
import httpx

from film2trello.http import raise_on_error


COLORS = {
    "20m": "blue",
    "30m": "sky",
    "45m": "green",
    "1h": "lime",
    "1.5h": "yellow",
    "2h": "orange",
    "2.5h": "red",
    "3+h": "purple",
}

THUMBNAIL_SIZE = (500, 500)

KVIFFTV_LABEL = dict(name="KVIFF.TV", color="black")


def get_trello_api(key: str, token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        base_url="https://trello.com/1/",
        params=dict(key=key, token=token),
        headers={
            "User-Agent": "film2trello (+https://github.com/honzajavorek/film2trello)"
        },
        http2=True,
        event_hooks={"response": [raise_on_error]},
    )


async def check_username(
    trello_api: httpx.AsyncClient,
    board_id: str,
    username: str,
) -> None:
    members = (await trello_api.get(f"/boards/{board_id}/members")).json()
    if username not in [member["username"] for member in members]:
        raise ValueError(f"User '{username}' is not allowed to the board")


async def get_working_lists_ids(
    trello_api: httpx.AsyncClient,
    board_id: str,
) -> list[str]:
    lists = (await trello_api.get(f"/boards/{board_id}/lists")).json()
    return [get_inbox_id(lists), get_archive_id(lists)]


async def fetch_cards(
    trello_api: httpx.AsyncClient,
    board_id: str,
    lists_ids: list[str],
) -> list[dict]:
    responses = await asyncio.gather(
        *(
            trello_api.get(f"/boards/{board_id}/lists/{list_id}/cards")
            for list_id in lists_ids
        )
    )
    return list(
        itertools.chain.from_iterable(response.json() for response in responses)
    )


async def update_card(
    trello_api: httpx.AsyncClient,
    card_id: str,
    card_data: dict,
) -> None:
    await trello_api.put(f"/cards/{card_id}/", json=card_data)


async def create_card(
    trello_api: httpx.AsyncClient,
    card_data: dict,
) -> str:
    response = await trello_api.post("/cards", json=card_data)
    return response.json()["id"]


async def join_card(
    trello_api: httpx.AsyncClient,
    card_id: str,
    username: str,
) -> None:
    card_members = (await trello_api.get(f"/cards/{card_id}/members")).json()
    if not_in_members(username, card_members):
        user_id = (await trello_api.get(f"/members/{username}")).json()["id"]
        await trello_api.post(
            f"/cards/{card_id}/members",
            json=dict(value=user_id),
        )


async def update_card_labels(
    trello_api: httpx.AsyncClient,
    card_id: str,
    labels: list[dict],
) -> None:
    card_labels = (await trello_api.get(f"/cards/{card_id}/labels")).json()
    labels = get_missing_labels(card_labels, labels)

    async def update_label(label: dict) -> None:
        try:
            await trello_api.post(f"/cards/{card_id}/labels", params=label)
        except httpx.HTTPStatusError as e:
            if "label is already on the card" not in e.response.text:
                raise e

    await asyncio.gather(*(update_label(label) for label in labels))


async def update_card_attachments(
    trello_api: httpx.AsyncClient,
    scraper: httpx.AsyncClient,
    card_id: str,
    page_urls: list[str],
    poster_url: str | None = None,
) -> None:
    attachments = (await trello_api.get(f"/cards/{card_id}/attachments")).json()
    page_urls = get_missing_attached_urls(attachments, page_urls)

    await asyncio.gather(
        *(
            trello_api.post(f"/cards/{card_id}/attachments", json=dict(url=page_url))
            for page_url in page_urls
        )
    )
    if not has_poster(attachments) and poster_url:
        response = await scraper.get(poster_url)
        await trello_api.post(
            f"/cards/{card_id}/attachments",
            files=dict(file=create_thumbnail(response.content)),
        )


def get_card_url(card_id: str) -> str:
    return f"https://trello.com/c/{card_id}"


def get_board_url(board_id: str) -> str:
    return f"https://trello.com/b/{board_id}"


def find_card_id(cards: list[dict], title: str, url: str) -> str | None:
    for card in cards:
        if title in card["name"] or url in card["desc"]:
            return card["id"]


def get_inbox_id(lists: list[dict]) -> str:
    return lists[0]["id"]


def get_archive_id(lists: list[dict]) -> str:
    return lists[-1]["id"]


def not_in_members(username, members) -> bool:
    return username not in [member["username"] for member in members]


def prepare_card_data(
    name: str,
    csfd_url: str,
    move_to_top: bool = False,
    move_to_list_id: str | None = None,
) -> dict:
    data = dict(name=name, desc=csfd_url)
    if move_to_top:
        data["pos"] = "top"
    if move_to_list_id:
        data["idList"] = move_to_list_id
    return data


def prepare_duration_labels(durations: list[int]) -> list[dict[str, str]]:
    labels = []
    for duration in durations:
        name = get_duration_bracket(duration)
        labels.append(dict(name=name, color=COLORS[name]))
    return labels


def get_duration_bracket(duration: int) -> str:
    duration_cca = math.floor(duration / 10.0) * 10
    if duration <= 20:
        return "20m"
    elif duration <= 30:
        return "30m"
    elif duration <= 45:
        return "45m"
    if duration <= 60:
        return "1h"
    if duration_cca <= 90:
        return "1.5h"
    if duration_cca <= 120:
        return "2h"
    if duration_cca <= 150:
        return "2.5h"
    else:
        return "3+h"


def get_missing_labels(existing_labels: list[dict], labels: list[dict]) -> list[dict]:
    names = {label["name"] for label in existing_labels}
    return [label for label in labels if label["name"] not in names]


def get_missing_attached_urls(
    existing_attachments: list[dict], urls: list[str]
) -> list[str]:
    existing_urls = {
        attachment["url"]
        for attachment in existing_attachments
        if attachment["name"] == attachment["url"]
    }
    return list(frozenset(urls) - existing_urls)


def has_poster(attachments) -> bool:
    for attachment in attachments:
        if len(attachment["previews"]):
            return True
    return False


def create_thumbnail(
    image_bytes: bytes,
) -> tuple[Literal["poster.jpg"], BytesIO, Literal["image/jpeg"]]:
    image = Image.open(image_bytes).convert("RGB")
    image.thumbnail(THUMBNAIL_SIZE)
    out_file = BytesIO()
    image.save(out_file, "JPEG")
    out_file.seek(0)
    return ("poster.jpg", out_file, "image/jpeg")
