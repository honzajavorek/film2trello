import logging
from functools import partial

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from film2trello.core import process_message


logger = logging.getLogger("film2trello.bot")


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    users: list[tuple[int, str]],
    board_url: str,
) -> None:
    user = update.effective_user
    if not user:
        raise ValueError("No user available")
    if not update.message:
        raise ValueError("No message available")
    await update.message.reply_html(
        f"Ahoj {user.mention_html()}! {help(board_url, dict(users)[user.id])}"
    )


async def help_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    users: list[tuple[int, str]],
    board_url: str,
) -> None:
    user = update.effective_user
    if not user:
        raise ValueError("No user available")
    if not update.message:
        raise ValueError("No message available")
    await update.message.reply_html(help(board_url, dict(users)[user.id]))


async def save(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    users: list[tuple[int, str]],
    board_url: str,
) -> None:
    user = update.effective_user
    if not user:
        raise ValueError("No user available")
    if not update.message:
        raise ValueError("No message available")
    try:
        state = await process_message(update.message.text or "")
    except Exception as e:
        logger.exception(e)
        await update.message.reply_html(
            f"Stala se nějaká chyba 😢\n\n"
            f"<pre>{e}</pre>\n\n"
            f"{help(board_url, dict(users)[user.id])}"
        )
    else:
        await update.message.reply_html(f"<pre>{state!r}</pre>")


def help(board_url: str, username: str) -> str:
    return (
        f"Můžeš mi posílat odkazy na filmy z KVIFF.TV nebo ČSFD a já je budu ukládat do tohoto Trella: {board_url} "
        f"Na kartičku přiřadím Trello uživatele <code>{username}</code>. "
        "Pokud pošleš odkaz na seriál, uložím ti jeho první sérii. "
        "Jestli chceš zaznamenat jinou sérii, musíš poslat odkaz přímo na ni. "
    )


def run(
    users: list[tuple[int, str]],
    board_url: str,
    telegram_token: str,
) -> None:
    user_ids = [user_id for user_id, _ in users]
    user_filter = filters.User(user_ids, allow_empty=False)
    logger.info(f"Interactions allowed only with these users: {user_ids!r}")

    application = Application.builder().token(telegram_token).build()
    application.add_handlers(
        [
            CommandHandler(
                "start",
                partial(start_command, users=users, board_url=board_url),
                user_filter,
            ),
            CommandHandler(
                "help",
                partial(help_command, users=users, board_url=board_url),
                user_filter,
            ),
            MessageHandler(
                user_filter & filters.TEXT & ~filters.COMMAND,
                partial(save, users=users, board_url=board_url),
            ),
        ]
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)
