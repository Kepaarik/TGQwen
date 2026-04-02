from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import AVAILABLE_CURRENCIES

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💸 Доход", callback_data="menu_income"),
        InlineKeyboardButton(text="💳 Расход", callback_data="menu_expense")
    )
    builder.row(InlineKeyboardButton(text="⚙️ Доп. меню", callback_data="menu_extra"))
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close"))
    return builder.as_markup()

def get_extra_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="💎 Мой баланс", callback_data="extra_my_balance"),
        InlineKeyboardButton(text="📊 Баланс всех", callback_data="extra_all_balance")
    )
    builder.row(
        InlineKeyboardButton(text="📅 Какой день?", callback_data="extra_day"),
        InlineKeyboardButton(text="📜 История", callback_data="extra_history")
    )
    builder.row(
        InlineKeyboardButton(text="🎉 События", callback_data="extra_events")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back_main"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close")
    )
    return builder.as_markup()

def get_currency_menu():
    builder = InlineKeyboardBuilder()
    rows = []
    for i in range(0, len(AVAILABLE_CURRENCIES), 2):
        row = []
        for curr in AVAILABLE_CURRENCIES[i:i+2]:
            row.append(InlineKeyboardButton(text=curr, callback_data=f"set_curr_{curr}"))
        rows.append(row)
    
    for row in rows:
        builder.row(*row)
        
    builder.row(InlineKeyboardButton(text="🔙 Отмена", callback_data="menu_cancel_action"))
    return builder.as_markup()

def get_events_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить", callback_data="event_add"))
    builder.row(
        InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back_main"),
        InlineKeyboardButton(text="❌ Закрыть", callback_data="menu_close")
    )
    return builder.as_markup()
