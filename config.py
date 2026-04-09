import logging
import os

from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv("TOKEN")
# Шлях до файлу бази даних.
# Файл створюється автоматично при першому запуску.
DATABASE = "bulls_cows.db"

# Telegram ID першого адміністратора.
# Дізнатися свій ID можна у @userinfobot.
# Цей користувач автоматично отримає роль admin при першому /start.
OWNER_ID = os.getenv("OWNER_ID")   # ← ЗАМІНІТЬ на свій Telegram ID!

# Кількість цифр у числі
DIGIT_COUNT = 4

# Налаштування логування
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("bulls_cows")