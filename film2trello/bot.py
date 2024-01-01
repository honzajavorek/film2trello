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


logger = logging.getLogger("film2trello.bot")


async def start_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    users: list[tuple[int, str]],
    board_url: str,
) -> None:
    user = update.effective_user
    if not user:
        raise ValueError(f"No user available")
    if not update.message:
        raise ValueError(f"No message available")
    await update.message.reply_html(
        f"Ahoj {user.mention_html()}! "
        f"Můžeš mi posílat odkazy na ČSFD a já je budu ukládat do tohoto Trella: {board_url} "
        f"Na kartičku přiřadím Trello uživatele <code>{dict(users)[user.id]}</code>."
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        logger.warning(f"No message available")
        return
    await update.message.reply_text("Help!")


async def save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        raise ValueError(f"No message available")
    text = update.message.text or ""
    await update.message.reply_text(
        f"Dostal jsem zprávu: {text} Výtečně! Akorát s ní zatím neumím nic dělat."
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
                help_command,
                user_filter,
            ),
            MessageHandler(
                user_filter & filters.TEXT & ~filters.COMMAND,
                save,
            ),
        ]
    )
    application.run_polling(allowed_updates=Update.ALL_TYPES)
