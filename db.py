from datetime import datetime

# aiosqlite — асинхронна обгортка для SQLite.
# Дозволяє працювати з БД без блокування бота.
import aiosqlite

from config import DATABASE, OWNER_ID, logger


async def init_db():
    """Створює таблиці в базі даних, якщо їх ще немає.

    CREATE TABLE IF NOT EXISTS — створює таблицю лише якщо вона
    не існує. Це безпечно викликати при кожному запуску бота.

    INTEGER PRIMARY KEY AUTOINCREMENT — унікальний ID, що
    автоматично збільшується з кожним новим записом (1, 2, 3...).

    UNIQUE — значення не може повторюватися (два користувачі
    не можуть мати однаковий telegram_id).

    NOT NULL — значення обов'язкове (не може бути порожнім).

    DEFAULT 'player' — якщо не вказати значення при INSERT,
    буде використано 'player'.
    """
    async with aiosqlite.connect(DATABASE) as db:
        # Таблиця користувачів
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                username    TEXT NOT NULL,
                role        TEXT NOT NULL DEFAULT 'player',
                created_at  TEXT NOT NULL
            )
        """)

        # Таблиця завершених ігор
        await db.execute("""
            CREATE TABLE IF NOT EXISTS games (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                secret      TEXT NOT NULL,
                attempts    INTEGER NOT NULL,
                won         INTEGER NOT NULL DEFAULT 0,
                played_at   TEXT NOT NULL
            )
        """)

        # commit() — зберігає зміни на диск.
        # Без commit() зміни залишаться лише в пам'яті і зникнуть.
        await db.commit()

    logger.info("База даних ініціалізована")


async def ensure_user(telegram_id: int, username: str) -> dict:
    """Реєструє користувача в БД (якщо ще не зареєстрований)
    і повертає його дані.

    Це і є АУТЕНТИФІКАЦІЯ: при кожному контакті ми ідентифікуємо
    користувача за telegram_id і переконуємося що він є в БД.

    INSERT OR IGNORE — якщо запис з таким telegram_id вже існує,
    нічого не робить (не створює дублікат і не кидає помилку).

    row_factory = aiosqlite.Row — дозволяє звертатися до стовпців
    за іменем (row["username"]) замість індексу (row[2]).
    """
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DATABASE) as db:
        # Визначаємо роль: OWNER_ID отримує admin, решта — player
        role = "admin" if telegram_id == OWNER_ID else "player"

        # INSERT OR IGNORE — вставляє лише якщо telegram_id ще немає в таблиці
        await db.execute(
            "INSERT OR IGNORE INTO users (telegram_id, username, role, created_at) "
            "VALUES (?, ?, ?, ?)",
            (telegram_id, username, role, now),
        )
        await db.commit()

        # Отримуємо дані користувача
        # row_factory дозволяє робити row["field"] замість row[2]
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()

        # dict(row) — перетворює Row у звичайний словник
        return dict(row)


async def get_user_role(telegram_id: int) -> str:
    """Повертає роль користувача ('admin' або 'player').

    Використовується для АВТОРИЗАЦІЇ — перевірки прав доступу.
    """
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "SELECT role FROM users WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()

        # Якщо користувача немає в БД — повертаємо None
        return row[0] if row else None


async def save_game(telegram_id: int, secret: str, attempts: int, won: bool):
    """Зберігає результат завершеної гри в БД.

    won зберігається як INTEGER: True → 1, False → 0
    (SQLite не має типу BOOLEAN, тому використовують 0/1).
    """
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DATABASE) as db:
        await db.execute(
            "INSERT INTO games (telegram_id, secret, attempts, won, played_at) "
            "VALUES (?, ?, ?, ?, ?)",
            (telegram_id, secret, attempts, int(won), now),
        )
        await db.commit()


async def get_user_stats(telegram_id: int) -> dict:
    """Повертає статистику гравця з БД.

    COUNT(*) — кількість рядків (ігор).
    SUM(won) — сума поля won (1 за кожну перемогу, 0 за програш).
    MIN(attempts) — мінімальна кількість спроб серед виграних ігор.
    WHERE won = 1 — фільтр лише по виграних іграх (для best_score).
    """
    async with aiosqlite.connect(DATABASE) as db:
        # Загальна кількість ігор та перемог
        cursor = await db.execute(
            "SELECT COUNT(*) as total, SUM(won) as wins FROM games WHERE telegram_id = ?",
            (telegram_id,),
        )
        row = await cursor.fetchone()
        total = row[0] or 0
        wins = row[1] or 0

        # Найкращий результат (мін. спроб серед перемог)
        cursor = await db.execute(
            "SELECT MIN(attempts) FROM games WHERE telegram_id = ? AND won = 1",
            (telegram_id,),
        )
        best_row = await cursor.fetchone()
        best = best_row[0]     # None якщо перемог не було

        return {
            "total": total,
            "wins": wins,
            "losses": total - wins,
            "best": best,
        }


async def get_leaderboard(limit: int = 10) -> list[dict]:
    """Повертає таблицю лідерів — топ гравців за мін. кількістю спроб.

    JOIN — об'єднує дані з двох таблиць (games та users) за спільним полем.
    GROUP BY — групує рядки за telegram_id (один рядок на гравця).
    ORDER BY — сортує за best_score (менше спроб = краще).
    LIMIT — обмежує кількість результатів.
    """
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("""
            SELECT
                u.username,
                MIN(g.attempts) as best_score,
                COUNT(g.id) as total_wins
            FROM games g
            JOIN users u ON g.telegram_id = u.telegram_id
            WHERE g.won = 1
            GROUP BY g.telegram_id
            ORDER BY best_score ASC
            LIMIT ?
        """, (limit,))

        rows = await cursor.fetchall()
        return [
            {"name": r[0], "best": r[1], "wins": r[2]}
            for r in rows
        ]


async def get_all_users() -> list[dict]:
    """Повертає список усіх зареєстрованих користувачів (для адміна)."""
    async with aiosqlite.connect(DATABASE) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT telegram_id, username, role, created_at FROM users ORDER BY created_at"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]


async def set_user_role(telegram_id: int, new_role: str) -> bool:
    """Змінює роль користувача. Повертає True якщо користувача знайдено."""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "UPDATE users SET role = ? WHERE telegram_id = ?",
            (new_role, telegram_id),
        )
        await db.commit()
        # cursor.rowcount — кількість змінених рядків (0 = не знайдено)
        return cursor.rowcount > 0


async def reset_user_stats(telegram_id: int) -> int:
    """Видаляє всі ігри користувача. Повертає кількість видалених записів."""
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute(
            "DELETE FROM games WHERE telegram_id = ?",
            (telegram_id,),
        )
        await db.commit()
        return cursor.rowcount


async def get_global_stats() -> dict:
    """Повертає загальну статистику бота (для адмін-панелі).

    Підраховує кількість користувачів, ігор та перемог.
    """
    async with aiosqlite.connect(DATABASE) as db:
        # Кількість користувачів
        cur = await db.execute("SELECT COUNT(*) FROM users")
        user_count = (await cur.fetchone())[0]

        # Кількість ігор і перемог
        cur = await db.execute("SELECT COUNT(*), SUM(won) FROM games")
        row = await cur.fetchone()
        game_count = row[0] or 0
        win_count = row[1] or 0

    return {
        "user_count": user_count,
        "game_count": game_count,
        "win_count": win_count,
    }