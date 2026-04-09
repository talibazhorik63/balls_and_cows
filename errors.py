from telegram.ext import ContextTypes

from config import logger


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Помилка: {context.error}", exc_info=context.error)
    if update and hasattr(update, "effective_message") and update.effective_message:
        await update.effective_message.reply_text("⚠️ Сталася помилка.")