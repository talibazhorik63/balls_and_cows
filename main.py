from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TOKEN, logger
from db import init_db
from handlers import (
    cmd_start,
    new_game,
    give_up,
    show_stats,
    show_leaderboard,
    admin_panel,
    admin_show_users,
    admin_show_stats,
    promote_user,
    reset_stats,
    handle_digit,
    handle_delete,
    handle_confirm,
    handle_retry,
    handle_inline_newgame,
    handle_noop,
)
from errors import error_handler


# ================================================================
# ФУНКЦІЯ post_init — ІНІЦІАЛІЗАЦІЯ БД ПРИ СТАРТІ БОТА
# ================================================================

async def post_init(application):
    """Викликається бібліотекою ПІСЛЯ створення Application, але ПЕРЕД
    початком обробки повідомлень. Ідеальне місце для ініціалізації БД.

    post_init — це «хук» (hook), який бібліотека викликає автоматично.
    Ми передаємо його через ApplicationBuilder().post_init(post_init).
    """
    await init_db()
    logger.info("post_init: БД готова")


def main():
    app = (
        ApplicationBuilder()
        .token(TOKEN)
        .concurrent_updates(True)
        .post_init(post_init)       # ← ініціалізація БД при старті
        .build()
    )

    # ── Команди ──
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("promote", promote_user))
    app.add_handler(CommandHandler("resetstats", reset_stats))

    # ── Reply-кнопки (навігація) ──
    app.add_handler(MessageHandler(filters.Regex(r"^🎮 Нова гра$"),      new_game))
    app.add_handler(MessageHandler(filters.Regex(r"^🏳️ Здатися$"),       give_up))
    app.add_handler(MessageHandler(filters.Regex(r"^📊 Статистика$"),    show_stats))
    app.add_handler(MessageHandler(filters.Regex(r"^🏆 Лідери$"),        show_leaderboard))
    app.add_handler(MessageHandler(filters.Regex(r"^⚙️ Адмін-панель$"),  admin_panel))

    # ── Inline-кнопки (ігровий процес) ──
    app.add_handler(CallbackQueryHandler(handle_digit,          pattern=r"^digit_\d$"))
    app.add_handler(CallbackQueryHandler(handle_delete,         pattern=r"^act_delete$"))
    app.add_handler(CallbackQueryHandler(handle_confirm,        pattern=r"^act_confirm$"))
    app.add_handler(CallbackQueryHandler(handle_retry,          pattern=r"^act_retry$"))
    app.add_handler(CallbackQueryHandler(handle_inline_newgame, pattern=r"^act_newgame$"))
    app.add_handler(CallbackQueryHandler(handle_noop,           pattern=r"^act_noop$"))

    # ── Inline-кнопки (адмін-панель) ──
    app.add_handler(CallbackQueryHandler(admin_show_users, pattern=r"^adm_users$"))
    app.add_handler(CallbackQueryHandler(admin_show_stats, pattern=r"^adm_stats$"))

    # ── Обробник помилок ──
    app.add_error_handler(error_handler)

    logger.info("🐂🐄 Бот запущено!")
    app.run_polling()


if __name__ == "__main__":
    main()