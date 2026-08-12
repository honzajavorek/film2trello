import html
import logging
from functools import partial

import httpx
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from film2trello.core import process_message
from film2trello.http import with_scraper
from film2trello.trello import get_board_url, with_trello_api


logger = logging.getLogger("film2trello.bot")


def run(
    users: list[tuple[int, str]],
    board_id: str,
    telegram_token: str,
    trello_key: str,
    trello_token: str,
) -> None:
    user_ids = [user_id for user_id, _ in users]
    user_filter = filters.User(user_ids, allow_empty=False)
    logger.info(f"Interactions allowed only with these users: {user_ids!r}")

    application = Application.builder().token(telegram_token).build()
    application.add_handlers(
        [
            CommandHandler(
                "start",
                partial(start_command, users=users, board_id=board_id),
                user_filter,
            ),
            CommandHandler(
                "help",
                partial(help_command, users=users, board_id=board_id),
                user_filter,
            ),
            MessageHandler(
                user_filter & filters.TEXT & ~filters.COMMAND,
                partial(
                    save,
                    users=users,
                    board_id=board_id,
                    trello_key=trello_key,
                    trello_token=trello_token,
                    secrets=[telegram_token, trello_key, trello_token],
                ),
            ),
        ]
    )

    logger.info("Starting bot")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    users: list[tuple[int, str]],
    board_id: str,
) -> None:
    user = update.effective_user
    if not user:
        raise ValueError("No user available")
    if not update.message:
        raise ValueError("No message available")
    await update.message.reply_html(
        f"Ahoj {user.mention_html()}! {get_help_text(board_id, dict(users)[user.id])}"
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    users: list[tuple[int, str]],
    board_id: str,
) -> None:
    user = update.effective_user
    if not user:
        raise ValueError("No user available")
    if not update.message:
        raise ValueError("No message available")
    await update.message.reply_html(get_help_text(board_id, dict(users)[user.id]))


@with_trello_api
@with_scraper
async def save(
    scraper: httpx.AsyncClient,
    trello_api: httpx.AsyncClient,
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    users: list[tuple[int, str]],
    board_id: str,
    secrets: list[str] | None = None,
) -> None:
    user = update.effective_user
    if user:
        username = dict(users)[user.id]
    else:
        raise ValueError("No user available")
    if not update.message:
        raise ValueError("No message available")

    reply = await update.message.reply_html("Processing…")
    try:
        async for message in process_message(
            scraper,
            trello_api,
            username,
            update.message.text or "",
            board_id,
        ):
            logger.info(f"Status: {message}")
            await reply.edit_text(
                message,
                parse_mode="HTML",
                disable_web_page_preview=True,
            )
    except Exception as exc:
        logger.exception("Error while processing the message")
        exc_text = str(exc)
        if secrets:
            exc_text = sanitize(exc_text, secrets)
        await update.message.reply_html(
            f"Stala se nějaká chyba 😢\n\n"
            f"<pre>{html.escape(exc_text)}</pre>\n\n"
            f"{get_help_text(board_id, username)}"
        )


def get_help_text(board_id: str, username: str) -> str:
    return (
        f"Můžeš mi posílat odkazy na filmy z KVIFF.TV nebo ČSFD a já je budu ukládat do tohoto Trella: {get_board_url(board_id)} "
        f"Na kartičku přiřadím Trello uživatele <code>{html.escape(username)}</code>. "
        "Pokud pošleš odkaz na seriál, uložím ti jeho první sérii. "
        "Jestli chceš zaznamenat jinou sérii, musíš poslat odkaz přímo na ni. "
    )


def sanitize(text: str, secrets: list[str]) -> str:
    for secret in secrets:
        text = text.replace(secret, "[SECRET]")
    return text
