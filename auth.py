import functools

from telegram import Update
from telegram.ext import ContextTypes

from config import logger
from db import get_user_role


def admin_only(func):
    """Декоратор: дозволяє виконання лише адміністраторам.

    Декоратор — це функція, що «обгортає» іншу функцію.
    @admin_only перед функцією — це те саме що:
        admin_command = admin_only(admin_command)

    functools.wraps(func) — зберігає ім'я та документацію
    оригінальної функції (без нього Python бачив би 'wrapper').
    """
    @functools.wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        role = await get_user_role(user_id)

        if role != "admin":
            logger.warning(
                f"Спроба доступу до {func.__name__} від "
                f"{update.effective_user.first_name} (id={user_id}, role={role})"
            )
            await update.effective_message.reply_text(
                "🚫 Ця команда доступна лише адміністраторам."
            )
            return

        # Роль admin — виконуємо оригінальну функцію
        return await func(update, context)

    return wrapper