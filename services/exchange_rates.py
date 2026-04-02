import httpx
import logging

logger = logging.getLogger(__name__)

async def get_exchange_rates():
    """Получает курсы из NBRB или резервного API (USD, EUR, CNY, RUB)."""
    url_nbrb = "https://api.nbrb.by/exrates/rates?periodicity=0"
    rates = {}
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
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
                    return rates
    except Exception as e:
        logger.warning(f"NBRB недоступен: {e}. Пробую резерв.")

    # Резервный международный API
    url_backup = "https://open.er-api.com/v6/latest/USD"
    try:
        async with httpx.AsyncClient(timeout=10.0) as c:
            resp = await c.get(url_backup)
            if resp.status_code == 200:
                data = resp.json().get("rates", {})
                usd_to_byn = data.get("BYN")
                if usd_to_byn:
                    return {
                        "USD": usd_to_byn,
                        "EUR": usd_to_byn / data.get("EUR", 1),
                        "CNY": usd_to_byn / data.get("CNY", 1),
                        "RUB": usd_to_byn / data.get("RUB", 1)
                    }
    except Exception as e:
        logger.error(f"Ошибка всех API: {e}")
    
    return None
