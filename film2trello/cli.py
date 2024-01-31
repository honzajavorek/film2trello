import asyncio
import logging

import click
from httpx import HTTPStatusError

from film2trello.bot import run as run_bot
from film2trello.core import process_inbox


logger = logging.getLogger("film2trello.cli")


def parse_user(user: str) -> tuple[int, str]:
    telegram_id, trello_username = user.split(":")
    return int(telegram_id), trello_username


board_id_option = click.option(
    "-b",
    "--board",
    "board_id",
    required=True,
    help="Trello board ID",
    default="zmyDOaFL",
)


trello_key_option = click.option(
    "--trello-key",
    required=True,
    help="Trello key",
    envvar="TRELLO_KEY",
)


trello_token_option = click.option(
    "--trello-token",
    required=True,
    help="Trello token",
    envvar="TRELLO_TOKEN",
)


@click.group()
@click.option(
    "-d",
    "--debug",
    is_flag=True,
    help="Set log level to DEBUG",
)
def main(debug: bool) -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.DEBUG if debug else logging.INFO,
    )
    for logger_name in ["httpx"]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)


@main.command()
@click.option(
    "-U",
    "--user",
    "users",
    help="User in format <telegram_id>:<trello_username>",
    type=parse_user,
    multiple=True,
    default=["119318534:honzajavorek", "175995069:zuzka"],
)
@board_id_option
@click.option(
    "--telegram-token",
    required=True,
    help="Telegram bot token",
    envvar="TELEGRAM_TOKEN",
)
@trello_key_option
@trello_token_option
def bot(
    users: list[tuple[int, str]],
    board_id: str,
    telegram_token: str,
    trello_key: str,
    trello_token: str,
) -> None:
    run_bot(users, board_id, telegram_token, trello_key, trello_token)


@main.command()
@board_id_option
@trello_key_option
@trello_token_option
def inbox(
    board_id: str,
    trello_key: str,
    trello_token: str,
) -> None:
    try:
        asyncio.run(
            process_inbox(
                board_id,
                trello_key=trello_key,
                trello_token=trello_token,
            )
        )
    except HTTPStatusError as exc:
        logger.exception(f"{exc}:\n\n{exc.response.text}\n\n")
        raise click.Abort()
