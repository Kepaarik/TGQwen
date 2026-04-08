from aiogram import Router, types, F
from keyboards.inline_kb import get_extra_menu, get_main_menu
from services.finance_calc import format_balance_tree
from services.date_utils import get_current_day
from database.transactions import get_user_history, get_user_last_active_dates, get_all_transactions
from datetime import datetime
from config import MOSCOW_TZ

router = Router()

@router.callback_query(F.data == "extra_my_balance")
async def show_my_balance(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    all_trans = await get_all_transactions(user_id)
    
    if not all_trans:
        text = "должен в кассу 0 BYN"
    else:
        # Находим последнюю транзакцию пользователя
        last_trans_date = max(t['date'] for t in all_trans)
        now = datetime.now(MOSCOW_TZ)
        days_since_payment = (now.date() - last_trans_date.astimezone(MOSCOW_TZ).date()).days
        amount_due = days_since_payment * 5
        text = f"должен в кассу {amount_due} BYN"
    
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_extra_menu())
    await callback.answer()

@router.callback_query(F.data == "extra_all_balance")
async def show_all_balance(callback: types.CallbackQuery):
    text = await format_balance_tree()
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_extra_menu())
    await callback.answer()

@router.callback_query(F.data == "extra_day")
async def show_current_day(callback: types.CallbackQuery):
    day = get_current_day()
    now = datetime.now(MOSCOW_TZ)
    stats = await get_user_last_active_dates()
    
    lines = [f"Сегодня <b>{day}-й день</b> марафона.", "---"]
    if stats:
        lines.append("<b>Статус участников:</b>")
        for u in stats:
            days_off = (now.date() - u['last_date'].astimezone(MOSCOW_TZ).date()).days
            status = "в строю" if days_off == 0 else f"отсутствует <b>{days_off} дн.</b>"
            lines.append(f"{u['n']}: {status}")
            
    await callback.message.edit_text("\n".join(lines), parse_mode="HTML", reply_markup=get_extra_menu())
    await callback.answer()

@router.callback_query(F.data == "extra_history")
async def show_history(callback: types.CallbackQuery):
    h = await get_user_history(callback.from_user.id, limit=10)
    res = []
    for t in h:
        sign = "+" if t['amount'] > 0 else "-"
        date_str = t['date'].astimezone(MOSCOW_TZ).strftime('%d.%m')
        res.append(f"<code>{date_str}</code> {sign} {abs(t['amount'])} {t['currency']}")
        
    text = "<b>Последние 10 операций:</b>\n\n" + ("\n".join(res) if res else "Пусто.")
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_extra_menu())
    await callback.answer()
