import logging
from pprint import pformat
from typing import AsyncGenerator, TypedDict

import httpx

from film2trello import csfd, trello, http


logger = logging.getLogger("film2trello.core")


class Film(TypedDict):
    title: str
    csfd_url: str
    poster_url: str | None
    kvifftv_url: str | None
    durations: list[int]


async def process_message(
    scraper: httpx.AsyncClient,
    trello_api: httpx.AsyncClient,
    username: str,
    message_text: str,
    board_id: str,
) -> AsyncGenerator[str, None]:
    yield "Figuring out CSFD.cz URL…"
    csfd_url = await get_csfd_url(scraper, message_text)

    yield "Scraping information from CSFD.cz…"
    pages = await get_csfd_pages(scraper, csfd_url)

    film = Film(
        csfd_url=csfd_url,
        title=csfd.parse_title(pages["target"]["html"]),
        poster_url=csfd.parse_poster_url(pages["target"]["html"]),
        durations=list(csfd.parse_durations(pages["target"]["html"])),
        kvifftv_url=csfd.parse_kvifftv_url(pages["parent"]["html"]),
    )
    logger.info(f"Film:\n{pformat(film)}")

    if username is not None:
        yield f"Checking if user '{username}' is allowed to the board"
        await trello.check_username(trello_api, board_id, username)

    if card_id:
        card_data = trello.prepare_card_data(film["title"], film["csfd_url"])
    else:
        yield "Analyzing columns, assuming first is inbox and last is archive"
        lists_ids = await trello.get_working_lists_ids(trello_api, board_id)
        inbox_list_id = lists_ids[0]

        yield "Checking if card already exists"
        cards = await trello.fetch_cards(trello_api, board_id, lists_ids)
        card_id = trello.find_card_id(cards, film["title"], film["csfd_url"])
        card_data = trello.prepare_card_data(
            film["title"],
            film["csfd_url"],
            move_to_top=True,
            move_to_list_id=inbox_list_id,
        )

    if card_id:
        yield f"Card already exists, updating: {trello.get_card_url(card_id)}"
        await trello.update_card(trello_api, card_id, card_data)
    else:
        yield "Card does not exist, creating"
        card_id = await trello.create_card(trello_api, card_data)
        yield f"Card created: {trello.get_card_url(card_id)}"

    if username is not None:
        yield "Updating members"
        await trello.join_card(trello_api, card_id, username)

    yield "Updating labels"
    labels = trello.prepare_duration_labels(film["durations"])
    if film.get("kvifftv_url"):
        labels.append(trello.KVIFFTV_LABEL)
    await trello.update_card_labels(trello_api, card_id, labels)

    yield "Updating attachments"
    await trello.update_card_attachments(
        trello_api,
        scraper,
        card_id,
        list(filter(None, [csfd_url, film["kvifftv_url"]])),
        film.get("poster_url"),
    )
    yield f"Done! This is your card: {trello.get_card_url(card_id)}"


async def get_csfd_url(scraper: httpx.AsyncClient, message_text: str) -> str:
    if input_url := csfd.get_kvifftv_url(message_text):
        logger.info(f"Detected KVIFF.TV URL, scraping: {input_url}")
        response = await scraper.get(input_url)
        if csfd_url := csfd.get_csfd_url(response.text):
            logger.info(f"Found CSFD.cz URL: {csfd_url}")
            return csfd_url
        raise ValueError("Could not find CSFD.cz URL")
    if input_url := csfd.get_csfd_url(message_text):
        logger.info(f"Detected CSFD.cz URL: {input_url}")
        return input_url
    raise ValueError("Could not find a valid film URL")


async def get_csfd_pages(
    scraper: httpx.AsyncClient,
    csfd_url: str,
) -> dict[str, http.Page]:
    pages = dict(csfd=await http.get_html(scraper, csfd_url))

    target_url = csfd.parse_target_url(pages["csfd"]["html"])
    try:
        pages["target"] = pages[target_url]
    except KeyError:
        logger.info(f"Different target URL, scraping: {target_url}")
        pages["target"] = await http.get_html(scraper, target_url)

    parent_url = csfd.get_parent_url(csfd_url)
    try:
        pages["parent"] = pages[parent_url]
    except KeyError:
        logger.info(f"Different parent URL, scraping: {parent_url}")
        pages["parent"] = await http.get_html(scraper, parent_url)

    return pages


async def process_inbox(board_id: str, trello_key: str, trello_token: str) -> None:
    # async with get_trello_api(trello_key, trello_token) as trello_api:
    #     lists = (await trello_api.get(f"/boards/{board_id}/lists")).json()
    #     inbox_list_id = trello.get_inbox_id(lists)
    #     archive_list_id = trello.get_archive_id(lists)

    #     years_ago = date.today() - timedelta(days=365 * 2)
    #     years_old_cards = (
    #         await trello_api.get(f"/lists/{inbox_list_id}/cards?before={years_ago}")
    #     ).json()
    #     logger.info(f"Found {len(years_old_cards)} years old cards")

    #     for card in years_old_cards:
    #         logger.info(
    #             f"Archiving card: {card['name']} {trello.get_card_url(card['id'])}"
    #         )
    #         await trello_api.put(
    #             f"/cards/{card['id']}/",
    #             json=dict(idList=archive_list_id),
    #         )

    #     cards = (await trello_api.get(f"/lists/{inbox_list_id}/cards")).json()
    #     for card in cards:
    #         logger.info(
    #             f"Processing card: {card['name']} {trello.get_card_url(card['id'])}"
    #         )
    #         if match := CSFD_URL_RE.search(card["desc"]):
    #             csfd_url = match.group(0)
    #             logger.info(f"CSFD.cz URL: {csfd_url}")
    #             async for message in process_url(
    #                 csfd_url,
    #                 board_id,
    #                 trello_key,
    #                 trello_token,
    #                 card_id=card["id"],
    #             ):
    #                 logger.info(f"Status: {message}")
    #         else:
    #             logger.info("Card description doesn't contain CSFD.cz URL")

    # logger.info("Sorting cards")
    # async with get_trello_api(trello_key, trello_token) as trello_api:
    #     for position, card in enumerate(sorted(cards, key=sort_inbox_key), start=1):
    #         logger.info(f"#{position}: {card['name']}")
    #         await trello_api.put(f"/cards/{card['id']}/", json=dict(pos=position))
    pass


def sort_inbox_key(card: dict) -> tuple[int, int, str]:
    return (1, 1, card["name"])
    # TODO: implement sorting
    # min_duration = min(film["durations"]) if (film and film["durations"]) else 1000
    # labels = [label["name"].lower() for label in card["labels"] or []]
    # is_available = 0 if (("kviff.tv" in labels) or ("stash" in labels)) else 1

    # return (min_duration, is_available, card["name"])
