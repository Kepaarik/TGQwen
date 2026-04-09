import asyncio
import httpx
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Кеш курсов — обновляется в фоне раз в день в 01:00
_cached_rates = None

def get_cached_rates():
    """Возвращает закешированные курсы мгновенно (без HTTP-запроса)."""
    return _cached_rates

async def _fetch_rates():
    """Получает курсы из NBRB или резервного API (USD, EUR, CNY, RUB)."""
    url_nbrb = "https://api.nbrb.by/exrates/rates?periodicity=0"
    rates = {}
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            resp = await c.get(url_nbrb)
            if resp.status_code == 200:
                data = resp.json()
                for item in data:
                    code = item.get('Cur_Abbreviation')
                    rate = item.get('Cur_OfficialRate')
                    scale = item.get('Cur_Scale', 1)
                    if code in ["USD", "EUR", "CNY", "RUB"]:
                        rates[code] = float(rate) / int(scale)
                if len(rates) >= 4:
                    logger.info(f"NBRB курсы получены: {rates}")
                    return rates
            else:
                logger.warning(f"NBRB вернул статус {resp.status_code}")
    except Exception as e:
        logger.warning(f"NBRB недоступен: {type(e).__name__}: {e}. Пробую резерв.")

    # Резервный международный API
    url_backup = "https://open.er-api.com/v6/latest/USD"
    try:
        async with httpx.AsyncClient(timeout=15.0) as c:
            resp = await c.get(url_backup)
            if resp.status_code == 200:
                data = resp.json().get("rates", {})
                usd_to_byn = data.get("BYN")
                if usd_to_byn:
                    result = {
                        "USD": usd_to_byn,
                        "EUR": usd_to_byn / data.get("EUR", 1),
                        "CNY": usd_to_byn / data.get("CNY", 1),
                        "RUB": usd_to_byn / data.get("RUB", 1)
                    }
                    logger.info(f"Резервные курсы получены: {result}")
                    return result
            else:
                logger.error(f"Резервный API вернул статус {resp.status_code}")
    except Exception as e:
        logger.error(f"Ошибка всех API: {type(e).__name__}: {e}")
    
    return None

async def refresh_rates_loop():
    """Фоновая задача: обновляет кеш курсов при старте и затем каждый день в 01:00."""
    global _cached_rates
    
    # Первое обновление при старте
    new_rates = await _fetch_rates()
    if new_rates:
        _cached_rates = new_rates
        logger.info("Кеш курсов обновлён при старте.")
    else:
        logger.warning("Не удалось обновить курсы при старте.")
    
    while True:
        # Вычисляем время до следующего обновления в 01:00
        now = datetime.now()
        next_update = now.replace(hour=1, minute=0, second=0, microsecond=0)
        
        # Если 01:00 уже прошло сегодня, планируем на завтра
        if now >= next_update:
            next_update += timedelta(days=1)
        
        delay = (next_update - now).total_seconds()
        logger.info(f"Следующее обновление курсов в {next_update.strftime('%Y-%m-%d %H:%M:%S')} (через {delay:.0f} секунд)")
        
        await asyncio.sleep(delay)
        
        new_rates = await _fetch_rates()
        if new_rates:
            _cached_rates = new_rates
            logger.info("Кеш курсов обновлён.")
        else:
            logger.warning("Не удалось обновить курсы, используем старый кеш.")
