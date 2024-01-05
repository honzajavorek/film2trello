import logging

import click

from film2trello import bot


logger = logging.getLogger("film2trello.cli")


def parse_user(user: str) -> tuple[int, str]:
    telegram_id, trello_username = user.split(":")
    return int(telegram_id), trello_username


@click.command()
@click.option(
    "-U",
    "--user",
    "users",
    help="User in format <telegram_id>:<trello_username>",
    type=parse_user,
    multiple=True,
    default=["119318534:honzajavorek", "175995069:zuzejk"],
)
@click.option(
    "-b",
    "--board",
    "board_id",
    required=True,
    help="Trello board ID",
    default="zmyDOaFL",
)
@click.option(
    "--telegram-token",
    required=True,
    help="Telegram bot token",
    envvar="TELEGRAM_TOKEN",
)
@click.option(
    "--trello-key",
    required=True,
    help="Trello key",
    envvar="TRELLO_KEY",
)
@click.option(
    "--trello-token",
    required=True,
    help="Trello token",
    envvar="TRELLO_TOKEN",
)
@click.option(
    "-l",
    "--log-level",
    help="Logging level",
    default="INFO",
)
def main(
    users: list[tuple[int, str]],
    board_id: str,
    telegram_token: str,
    trello_key: str,
    trello_token: str,
    log_level: str,
) -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, log_level.upper()),
    )
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logger.info("Starting bot")
    bot.run(users, board_id, telegram_token, trello_key, trello_token)
