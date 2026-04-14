from database.transactions import get_all_transactions
from services.exchange_rates import get_cached_rates
from config import AVAILABLE_CURRENCIES, CURRENCY_SYMBOLS

async def get_personal_wallet_text(user_id: int):
    all_trans = await get_all_transactions(user_id)
    balances = {c: 0.0 for c in AVAILABLE_CURRENCIES}
    
    if all_trans:
        for t in all_trans:
            cur = t["currency"]
            amt = t["amount"]
            if cur in balances:
                balances[cur] += amt
    
    rates = get_cached_rates()
    lines = ["◆ <b>Баланс</b>\n"]
    for curr in AVAILABLE_CURRENCIES:
        symbol = CURRENCY_SYMBOLS[curr]
        bal = balances[curr]
        if curr == "BYN":
            lines.append(f"• {curr}: {bal:.2f} Br")
        else:
            if rates:
                r = rates.get(curr, 0)
                if curr == "CNY":
                    lines.append(f"• {curr}: {bal:.2f} {symbol} (10{symbol}={r*10:.2f}Br)")
                else:
                    lines.append(f"• {curr}: {bal:.2f} {symbol} (1{symbol}={r:.2f}Br)")
            else:
                lines.append(f"• {curr}: {bal:.2f} {symbol}")
        
    return "\n".join(lines)

async def format_balance_tree(user_id=None):
    all_trans = await get_all_transactions(user_id)
    if not all_trans: return "Данных нет."
    
    rates = get_cached_rates()
    if not rates: return "Курсы ещё загружаются, попробуйте через пару секунд."

    u_data = {}
    total_all_byn = 0.0

    for t in all_trans:
        uid = t["user_id"]
        if uid not in u_data: 
            u_data[uid] = {"name": t.get("user_name", "User"), "bals": {}}
        
        cur, amt = t["currency"], t["amount"]
        u_data[uid]["bals"][cur] = u_data[uid]["bals"].get(cur, 0) + amt
        total_all_byn += amt if cur == "BYN" else amt * rates.get(cur, 0)

    header = f"Курсы: USD($): {rates['USD']:.3f}, EUR(€): {rates['EUR']:.3f}, CNY(¥): {rates['CNY']:.3f}\n"
    lines = [header]
    
    for uid, data in u_data.items():
        active = {k: v for k, v in data["bals"].items() if round(v, 2) != 0}
        if active:
            lines.append(f"<b>{data['name']}</b>")
            for cur in sorted(active.keys()):
                val = active[cur]
                symbol = CURRENCY_SYMBOLS.get(cur, cur)
                if cur == "BYN":
                    lines.append(f"  ┗ BYN: <code>{val:,.2f}</code> Br")
                else:
                    r = rates.get(cur, 0)
                    if cur == "CNY":
                        lines.append(f"  ┗ {cur}: <code>{val:,.2f}</code> {symbol} (10{symbol}={r*10:.2f}Br)")
                    else:
                        lines.append(f"  ┗ {cur}: <code>{val:,.2f}</code> {symbol} (1{symbol}={r:.2f}Br)")
    
    lines.append(f"\n<b>Итого:</b> <code>{total_all_byn:,.2f} BYN</code>")
    return "\n".join(lines)

async def format_single_user_balance(user_id: int):
    """Форматирует баланс одного пользователя в стиле 'баланс всех' с приблизительной суммой"""
    all_trans = await get_all_transactions(user_id)
    if not all_trans: 
        return "Данных нет."
    
    rates = get_cached_rates()
    if not rates: 
        return "Курсы ещё загружаются, попробуйте через пару секунд."

    # Собираем данные по пользователю
    user_data = {"name": "", "bals": {}}
    total_byn = 0.0

    for t in all_trans:
        uid = t["user_id"]
        if not user_data["name"]:
            user_data["name"] = t.get("user_name", "User")
        
        cur, amt = t["currency"], t["amount"]
        user_data["bals"][cur] = user_data["bals"].get(cur, 0) + amt
        total_byn += amt if cur == "BYN" else amt * rates.get(cur, 0)

    lines = []
    
    active = {k: v for k, v in user_data["bals"].items() if round(v, 2) != 0}
    if active:
        lines.append(f"<b>{user_data['name']}</b>")
        for cur in sorted(active.keys()):
            val = active[cur]
            symbol = CURRENCY_SYMBOLS.get(cur, cur)
            if cur == "BYN":
                lines.append(f"  ┗ BYN: <code>{val:,.2f}</code> Br")
            else:
                lines.append(f"  ┗ {cur}: <code>{val:,.2f}</code> {symbol}")
    
    lines.append(f"\n<b>Итого:</b> <code>{total_byn:,.2f} BYN</code>")
    return "\n".join(lines)
