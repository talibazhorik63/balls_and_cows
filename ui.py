from telegram import (
    ReplyKeyboardMarkup,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import DIGIT_COUNT
from db import get_user_role


# ── Inline-клавіатура — цифровий набірник ──

def build_game_text(entered: list[str], history: list[str]) -> str:
    """Формує текст ігрового повідомлення з дисплеєм та історією."""
    display_parts = []
    for i in range(DIGIT_COUNT):
        if i < len(entered):
            display_parts.append(f"[ {entered[i]} ]")
        else:
            display_parts.append("[ _ ]")
    display = "  ".join(display_parts)

    text = f"🐂🐄 *Бики та Корови*\n\n🔢 Ваше число:\n`{display}`"

    if history:
        text += "\n\n📜 *Спроби:*\n"
        recent = history[-8:]
        text += "\n".join(recent)
        if len(history) > 8:
            text += f"\n_...ще {len(history) - 8}_"

    return text


def build_numpad(entered: list[str]) -> InlineKeyboardMarkup:
    """Будує inline-клавіатуру з цифрами (натиснуті зникають)."""
    available = [d for d in "1234567890" if d not in entered]

    rows = []
    for i in range(0, len(available), 5):
        chunk = available[i:i + 5]
        row = [
            InlineKeyboardButton(d, callback_data=f"digit_{d}")
            for d in chunk
        ]
        rows.append(row)

    control_row = []
    if entered:
        control_row.append(InlineKeyboardButton("⌫ Стерти", callback_data="act_delete"))
    else:
        control_row.append(InlineKeyboardButton("⌫", callback_data="act_noop"))

    if len(entered) == DIGIT_COUNT:
        control_row.append(InlineKeyboardButton("✅ Підтвердити", callback_data="act_confirm"))
    else:
        remaining = DIGIT_COUNT - len(entered)
        control_row.append(InlineKeyboardButton(f"({remaining})", callback_data="act_noop"))

    rows.append(control_row)
    return InlineKeyboardMarkup(rows)


# ── Reply-клавіатура — навігація ──

# Клавіатура для звичайного гравця
PLAYER_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🎮 Нова гра", "🏳️ Здатися"],
        ["📊 Статистика", "🏆 Лідери"],
    ],
    resize_keyboard=True,
)

# Клавіатура для адміністратора — додатковий рядок з адмін-кнопками.
# Адміністратор бачить усе те саме, що й гравець, плюс кнопку «⚙️ Адмін».
ADMIN_KEYBOARD = ReplyKeyboardMarkup(
    [
        ["🎮 Нова гра", "🏳️ Здатися"],
        ["📊 Статистика", "🏆 Лідери"],
        ["⚙️ Адмін-панель"],
    ],
    resize_keyboard=True,
)


async def get_keyboard_for_user(telegram_id: int) -> ReplyKeyboardMarkup:
    """Повертає відповідну reply-клавіатуру залежно від ролі.

    Це приклад АВТОРИЗАЦІЇ на рівні інтерфейсу: адмін бачить
    додаткову кнопку, звичайний гравець — ні.
    """
    role = await get_user_role(telegram_id)
    if role == "admin":
        return ADMIN_KEYBOARD
    return PLAYER_KEYBOARD