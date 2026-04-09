from telegram import Update
from telegram.ext import ContextTypes

from config import logger
from db import ensure_user, save_game, get_user_stats, get_leaderboard
from game import generate_secret
from ui import build_game_text, build_numpad, get_keyboard_for_user


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /start — реєстрація та привітання."""
    user = update.effective_user

    # АУТЕНТИФІКАЦІЯ: реєструємо користувача в БД (або знаходимо існуючого)
    user_data = await ensure_user(user.id, user.first_name)
    role_label = "👑 Адміністратор" if user_data["role"] == "admin" else "🎮 Гравець"

    logger.info(f"/start від {user.first_name} (id={user.id}, role={user_data['role']})")

    # Показуємо клавіатуру відповідно до ролі
    keyboard = await get_keyboard_for_user(user.id)

    await update.message.reply_text(
        f"👋 Привіт, *{user.first_name}*!\n"
        f"Роль: {role_label}\n\n"
        "Я — бот-гра *«🐂 Бики та 🐄 Корови»*!\n\n"
        "🎯 Я загадую 4-значне число з унікальними цифрами.\n"
        "Набирай число на клавіатурі під повідомленням:\n"
        "  🐂 *Бик* — цифра на правильній позиції\n"
        "  🐄 *Корова* — цифра є, але не на тій позиції\n\n"
        "Натисни *🎮 Нова гра* щоб почати!",
        parse_mode="Markdown",
        reply_markup=keyboard,
    )


async def new_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Починає нову гру."""
    user = update.effective_user
    await ensure_user(user.id, user.first_name)

    secret = generate_secret()
    logger.info(f"Нова гра: {user.first_name}, secret={secret}")

    # Зберігаємо ігровий стан (поточна гра — в пам'яті, бо вона ще не завершена)
    context.user_data["secret"] = secret
    context.user_data["entered"] = []
    context.user_data["attempts"] = 0
    context.user_data["history"] = []

    text = build_game_text([], [])
    keyboard = build_numpad([])

    sent = await update.effective_message.reply_text(
        text, parse_mode="Markdown", reply_markup=keyboard,
    )
    context.user_data["game_msg_id"] = sent.message_id
    context.user_data["game_chat_id"] = sent.chat.id


async def give_up(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Гравець здається."""
    secret = context.user_data.get("secret")
    if not secret:
        await update.message.reply_text("❌ Немає активної гри.")
        return

    attempts = context.user_data.get("attempts", 0)

    # Зберігаємо програну гру в БД
    await save_game(update.effective_user.id, secret, attempts, won=False)

    context.user_data["secret"] = None

    await update.message.reply_text(
        f"🏳️ Здав(ла)ся після *{attempts}* спроб.\n"
        f"Загадане число: *{secret}*",
        parse_mode="Markdown",
    )

    # Прибираємо inline-клавіатуру з ігрового повідомлення
    try:
        await context.bot.edit_message_reply_markup(
            chat_id=context.user_data.get("game_chat_id"),
            message_id=context.user_data.get("game_msg_id"),
            reply_markup=None,
        )
    except Exception:
        pass


async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує статистику з БД."""
    stats = await get_user_stats(update.effective_user.id)

    best_str = f"*{stats['best']}* спроб" if stats["best"] else "—"

    await update.message.reply_text(
        f"📊 *Твоя статистика:*\n\n"
        f"🏆 Виграно: *{stats['wins']}*\n"
        f"🏳️ Програно: *{stats['losses']}*\n"
        f"🎮 Всього ігор: *{stats['total']}*\n"
        f"⭐ Найкращий результат: {best_str}\n\n"
        f"_Дані зберігаються у базі даних і не зникнуть при перезапуску бота._",
        parse_mode="Markdown",
    )


async def show_leaderboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показує таблицю лідерів з БД."""
    leaders = await get_leaderboard()

    if not leaders:
        await update.message.reply_text("🏆 Ще ніхто не виграв! Будь першим!")
        return

    medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
    lines = ["🏆 *Таблиця лідерів:*\n"]
    for i, p in enumerate(leaders):
        lines.append(f"{medals[i]} {i+1}. {p['name']} — *{p['best']}* спроб ({p['wins']} перемог)")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")