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

def get_days_until(date_text, recurrence='yearly'):
    """Считает, сколько дней осталось до следующего наступления события."""
    try:
        today = datetime.now(MOSCOW_TZ).date()
        parts = date_text.strip().replace(",", ".").split('.')
        day, month = int(parts[0]), int(parts[1])
        
        if recurrence == 'нет' or recurrence is None:
            # Для событий без повторения не возвращаем количество дней
            return None
        
        if recurrence == 'yearly':
            target_date = datetime(today.year, month, day).date()
            if target_date < today:
                target_date = target_date.replace(year=today.year + 1)
        elif recurrence == 'monthly':
            # Для ежемесячных - считаем до того же числа в следующем месяце
            if today.day < day:
                target_date = today.replace(day=day)
            else:
                # Если число уже прошло в этом месяце, берем следующий месяц
                if today.month == 12:
                    target_date = today.replace(year=today.year + 1, month=1, day=day)
                else:
                    target_date = today.replace(month=today.month + 1, day=day)
        elif recurrence == 'weekly':
            # Для еженедельных - считаем до следующего такого же дня недели
            target_weekday = datetime(today.year, month, day).weekday()
            days_ahead = target_weekday - today.weekday()
            if days_ahead < 0:
                days_ahead += 7
            if days_ahead == 0:
                days_ahead = 7  # Если сегодня тот же день, считаем до следующей недели
            from datetime import timedelta
            target_date = today + timedelta(days=days_ahead)
        else:
            # По умолчанию считаем как ежегодное
            target_date = datetime(today.year, month, day).date()
            if target_date < today:
                target_date = target_date.replace(year=today.year + 1)
        
        delta = (target_date - today).days
        if delta == 0: return "сегодня!"
        if delta == 1: return "завтра!"
        return f"осталось {delta} дн."
    except:
        return None
