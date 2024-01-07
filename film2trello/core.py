import logging
from pprint import pformat
from typing import AsyncGenerator, TypedDict

from film2trello import csfd, trello
from film2trello.http import get_html, get_scraper


logger = logging.getLogger("film2trello.core")


async def process_message(
    username: str,
    message_text: str,
    board_id: str,
    trello_key: str,
    trello_token: str,
) -> AsyncGenerator[str, None]:
    if input_url := csfd.get_kvifftv_url(message_text):
        yield f"Detected KVIFF.TV URL, scraping: {input_url}"
        async with get_scraper() as scraper:
            response = await scraper.get(input_url)
        csfd_url = csfd.get_csfd_url(response.text)
        if csfd_url is None:
            raise ValueError("Could not find CSFD.cz URL")
    elif input_url := csfd.get_csfd_url(message_text):
        yield f"Detected CSFD.cz URL: {input_url}"
        csfd_url = input_url
    else:
        raise ValueError("Could not find a valid film URL")

    async for message in process_url(
        csfd_url,
        board_id,
        trello_key,
        trello_token,
        username=username,
    ):
        yield message


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


class Film(TypedDict):
    title: str
    csfd_url: str
    poster_url: str | None
    kvifftv_url: str | None
    durations: list[int]


async def process_url(
    csfd_url: str,
    board_id: str,
    trello_key: str,
    trello_token: str,
    card_id: str | None = None,
    username: str | None = None,
) -> AsyncGenerator[str, None]:
    scraper = get_scraper()
    trello_api = trello.get_trello_api(trello_key, trello_token)
    try:
        yield f"Scraping CSFD.cz URL: {csfd_url}"
        pages = dict(csfd=await get_html(scraper, csfd_url))

        target_url = csfd.parse_target_url(pages["csfd"]["html"])
        try:
            pages["target"] = pages[target_url]
        except KeyError:
            yield f"Detected different target URL, scraping: {target_url}"
            pages["target"] = await get_html(scraper, target_url)

        parent_url = csfd.get_parent_url(csfd_url)
        try:
            pages["parent"] = pages[parent_url]
        except KeyError:
            yield f"Detected different parent URL, scraping: {parent_url}"
            pages["parent"] = await get_html(scraper, parent_url)

        film = Film(
            csfd_url=csfd_url,
            title=csfd.parse_title(pages["target"]["html"]),
            poster_url=csfd.parse_poster_url(pages["target"]["html"]),
            durations=list(csfd.parse_durations(pages["target"]["html"])),
            kvifftv_url=csfd.parse_kvifftv_url(pages["parent"]["html"]),
        )
        logger.debug(f"Film:\n{pformat(film)}")

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
    finally:
        await scraper.aclose()
        await trello_api.aclose()


def sort_inbox_key(card: dict) -> tuple[int, int, str]:
    return (1, 1, card["name"])
    # TODO: implement sorting
    # min_duration = min(film["durations"]) if (film and film["durations"]) else 1000
    # labels = [label["name"].lower() for label in card["labels"] or []]
    # is_available = 0 if (("kviff.tv" in labels) or ("stash" in labels)) else 1

    # return (min_duration, is_available, card["name"])
