from datetime import datetime
from config import MOSCOW_TZ, START_DATE

def get_current_day():
    now = datetime.now(MOSCOW_TZ)
    return (now.date() - START_DATE.date()).days + 1

def format_date_fancy(date_text):
    try:
        parts = date_text.strip().replace(",", ".").split('.')
        day, month = int(parts[0]), int(parts[1])
        months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
        return f"{day} {months[month-1]}"
    except: return date_text

def get_days_until(date_text):
    """Считает, сколько дней осталось до события (ежегодного)."""
    try:
        today = datetime.now(MOSCOW_TZ).date()
        parts = date_text.strip().replace(",", ".").split('.')
        day, month = int(parts[0]), int(parts[1])
        
        target_date = datetime(today.year, month, day).date()
        if target_date < today:
            target_date = target_date.replace(year=today.year + 1)
        
        delta = (target_date - today).days
        if delta == 0: return "сегодня!"
        if delta == 1: return "завтра!"
        return f"осталось {delta} дн."
    except:
        return None
