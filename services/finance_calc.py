from database.transactions import get_all_transactions
from services.exchange_rates import get_exchange_rates

async def format_balance_tree(user_id=None):
    all_trans = await get_all_transactions(user_id)
    if not all_trans: return "Данных нет."
    
    rates = await get_exchange_rates()
    if not rates: return "Ошибка курсов. BYN не рассчитан."

    u_data = {}
    total_all_byn = 0.0

    for t in all_trans:
        uid = t["user_id"]
        if uid not in u_data: 
            u_data[uid] = {"name": t.get("user_name", "User"), "bals": {}}
        
        cur, amt = t["currency"], t["amount"]
        u_data[uid]["bals"][cur] = u_data[uid]["bals"].get(cur, 0) + amt
        total_all_byn += amt if cur == "BYN" else amt * rates.get(cur, 0)

    header = f"Курсы: USD: {rates['USD']:.3f}, EUR: {rates['EUR']:.3f}, CNY: {rates['CNY']:.3f}\n"
    lines = [header]
    
    for uid, data in u_data.items():
        active = {k: v for k, v in data["bals"].items() if round(v, 2) != 0}
        if active:
            lines.append(f"<b>{data['name']}</b>")
            for cur in sorted(active.keys()):
                val = active[cur]
                if cur == "BYN":
                    lines.append(f"  ┗ BYN: <code>{val:,.2f}</code>")
                else:
                    r = rates.get(cur, 0)
                    lines.append(f"  ┗ {cur}: <code>{val:,.2f}</code> <i>(~{val*r:,.2f} BYN)</i>")
    
    lines.append(f"\n<b>Итого:</b> <code>{total_all_byn:,.2f} BYN</code>")
    return "\n".join(lines)
