from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import logger
from db import get_user_role, get_all_users, get_global_stats, set_user_role, reset_user_stats
from auth import admin_only


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує адмін-панель (inline-кнопки).

    Спочатку перевіряємо роль — якщо не admin, відхиляємо.
    """
    role = await get_user_role(update.effective_user.id)
    if role != "admin":
        await update.message.reply_text("🚫 Доступ заборонено.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Всі користувачі", callback_data="adm_users")],
        [InlineKeyboardButton("📈 Загальна статистика", callback_data="adm_stats")],
    ])

    await update.message.reply_text(
        "⚙️ *Адмін-панель*\n\nОберіть дію:",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def admin_show_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує список усіх користувачів (тільки для admin)."""
    query = update.callback_query
    await query.answer()

    # Перевірка авторизації
    role = await get_user_role(update.effective_user.id)
    if role != "admin":
        await query.answer("🚫 Доступ заборонено!", show_alert=True)
        return

    users = await get_all_users()

    if not users:
        await query.edit_message_text("Немає зареєстрованих користувачів.")
        return

    lines = ["👥 *Зареєстровані користувачі:*\n"]
    for u in users:
        role_icon = "👑" if u["role"] == "admin" else "👤"
        lines.append(
            f"{role_icon} {u['username']} "
            f"(ID: `{u['telegram_id']}`, роль: {u['role']})"
        )

    lines.append(f"\nВсього: *{len(users)}* користувачів")
    lines.append("\n_Щоб призначити адміна:_\n`/promote <telegram_id>`")
    lines.append("_Щоб скинути статистику:_\n`/resetstats <telegram_id>`")

    await query.edit_message_text(
        "\n".join(lines),
        parse_mode="Markdown",
    )


async def admin_show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує загальну статистику бота (тільки для admin)."""
    query = update.callback_query
    await query.answer()

    role = await get_user_role(update.effective_user.id)
    if role != "admin":
        await query.answer("🚫 Доступ заборонено!", show_alert=True)
        return

    stats = await get_global_stats()
    user_count = stats["user_count"]
    game_count = stats["game_count"]
    win_count = stats["win_count"]

    # Відсоток перемог (захист від ділення на 0)
    win_rate = (win_count / game_count * 100) if game_count > 0 else 0

    await query.edit_message_text(
        f"📈 *Загальна статистика бота:*\n\n"
        f"👥 Користувачів: *{user_count}*\n"
        f"🎮 Ігор зіграно: *{game_count}*\n"
        f"🏆 Перемог: *{win_count}* ({win_rate:.0f}%)\n"
        f"🏳️ Програшів: *{game_count - win_count}*",
        parse_mode="Markdown",
    )


@admin_only
async def promote_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /promote <telegram_id> — призначає адміністратора.

    @admin_only — декоратор перевіряє роль ПЕРЕД виконанням функції.
    Якщо роль не admin — функція не виконається, гравець побачить відмову.
    """
    if not context.args:
        await update.message.reply_text(
            "Використання: `/promote <telegram_id>`",
            parse_mode="Markdown",
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID має бути числом.")
        return

    success = await set_user_role(target_id, "admin")

    if success:
        logger.info(f"Користувач {target_id} отримав роль admin")
        await update.message.reply_text(
            f"✅ Користувач `{target_id}` тепер адміністратор.",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(f"❌ Користувача з ID `{target_id}` не знайдено.",
                                        parse_mode="Markdown")


@admin_only
async def reset_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /resetstats <telegram_id> — скидає статистику гравця."""
    if not context.args:
        await update.message.reply_text(
            "Використання: `/resetstats <telegram_id>`",
            parse_mode="Markdown",
        )
        return

    try:
        target_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text("❌ ID має бути числом.")
        return

    deleted = await reset_user_stats(target_id)

    logger.info(f"Скинуто {deleted} ігор для {target_id}")
    await update.message.reply_text(
        f"✅ Видалено *{deleted}* ігор для користувача `{target_id}`.",
        parse_mode="Markdown",
    )