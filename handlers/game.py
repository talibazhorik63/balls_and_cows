from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes

from config import DIGIT_COUNT
from db import save_game
from game import generate_secret, count_bulls_and_cows
from ui import build_game_text, build_numpad


async def handle_digit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Натискання цифрової кнопки — додає цифру до набору."""
    query = update.callback_query
    await query.answer()

    if not context.user_data.get("secret"):
        await query.answer("Немає активної гри!", show_alert=True)
        return

    digit = query.data.split("_")[1]
    entered = context.user_data.get("entered", [])

    if len(entered) >= DIGIT_COUNT or digit in entered:
        return

    entered.append(digit)
    context.user_data["entered"] = entered

    history = context.user_data.get("history", [])
    await query.edit_message_text(
        build_game_text(entered, history),
        parse_mode="Markdown",
        reply_markup=build_numpad(entered),
    )


async def handle_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка ⌫ — видаляє останню цифру."""
    query = update.callback_query
    await query.answer()

    entered = context.user_data.get("entered", [])
    if not entered:
        return

    entered.pop()
    context.user_data["entered"] = entered

    history = context.user_data.get("history", [])
    await query.edit_message_text(
        build_game_text(entered, history),
        parse_mode="Markdown",
        reply_markup=build_numpad(entered),
    )


async def handle_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка ✅ — підтверджує спробу, перевіряє биків та корів."""
    query = update.callback_query

    secret = context.user_data.get("secret")
    entered = context.user_data.get("entered", [])

    if not secret or len(entered) != DIGIT_COUNT:
        await query.answer("Набери всі цифри!", show_alert=True)
        return

    guess_str = "".join(entered)
    bulls, cows = count_bulls_and_cows(secret, guess_str)

    context.user_data["attempts"] = context.user_data.get("attempts", 0) + 1
    attempts = context.user_data["attempts"]

    result_line = (
        f"#{attempts}: `{guess_str}` → "
        f"{'🐂' * bulls}{'🐄' * cows} ({bulls}Б {cows}К)"
    )
    history = context.user_data.get("history", [])
    history.append(result_line)
    context.user_data["history"] = history

    # ── ПЕРЕМОГА ──
    if bulls == DIGIT_COUNT:
        await query.answer("🎉 Перемога!", show_alert=True)

        # Зберігаємо виграну гру в БД
        await save_game(update.effective_user.id, secret, attempts, won=True)

        context.user_data["secret"] = None

        text = (
            f"🎉 *ПЕРЕМОГА!*\n\n"
            f"Число: *{secret}*\n"
            f"Спроб: *{attempts}*\n\n"
            f"📜 *Спроби:*\n" + "\n".join(history)
        )

        await query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎮 Ще гру!", callback_data="act_newgame")],
            ]),
        )
        return

    # ── ГРА ПРОДОВЖУЄТЬСЯ ──
    await query.answer(f"{bulls}🐂 {cows}🐄")
    context.user_data["entered"] = []

    text = build_game_text([], history)
    text += f"\n\n📌 *Остання:* {result_line}"

    await query.edit_message_text(
        text, parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔢 Далі", callback_data="act_retry")],
        ]),
    )


async def handle_retry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Кнопка «Далі» — показує порожній numpad для наступної спроби."""
    query = update.callback_query
    await query.answer()

    if not context.user_data.get("secret"):
        await query.answer("Гру завершено!", show_alert=True)
        return

    context.user_data["entered"] = []
    history = context.user_data.get("history", [])

    await query.edit_message_text(
        build_game_text([], history),
        parse_mode="Markdown",
        reply_markup=build_numpad([]),
    )


async def handle_inline_newgame(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Inline-кнопка «Ще гру!» після перемоги."""
    query = update.callback_query
    await query.answer()

    secret = generate_secret()
    context.user_data["secret"] = secret
    context.user_data["entered"] = []
    context.user_data["attempts"] = 0
    context.user_data["history"] = []

    await query.edit_message_text(
        build_game_text([], []),
        parse_mode="Markdown",
        reply_markup=build_numpad([]),
    )


async def handle_noop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Неактивна кнопка — просто прибираємо індикатор."""
    await update.callback_query.answer()