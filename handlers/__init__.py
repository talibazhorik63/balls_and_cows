from handlers.nav import (
    cmd_start,
    new_game,
    give_up,
    show_stats,
    show_leaderboard,
)
from handlers.admin import (
    admin_panel,
    admin_show_users,
    admin_show_stats,
    promote_user,
    reset_stats,
)
from handlers.game import (
    handle_digit,
    handle_delete,
    handle_confirm,
    handle_retry,
    handle_inline_newgame,
    handle_noop,