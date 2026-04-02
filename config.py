import os
from pytz import timezone
from datetime import datetime

# Настройки бота
BOT_TOKEN = os.getenv("BOT_TOKEN", "8788194731:AAGKYQ6ur_aR5sh4INVRqSNNl8f_I3dXLfs")
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017/") # Будет браться с Render
PORT = int(os.getenv("PORT", 8080))

# Часовые пояса и даты марафона
MOSCOW_TZ = timezone("Europe/Moscow")
START_DATE = datetime(2025, 10, 28, tzinfo=MOSCOW_TZ)

# Валюты
AVAILABLE_CURRENCIES = ['BYN', 'USD', 'EUR', 'CNY']
CURRENCY_SYMBOLS = {
    'BYN': 'Br',
    'USD': '$',
    'EUR': '€',
    'CNY': '¥'
}
