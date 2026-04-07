from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import AVAILABLE_CURRENCIES

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="▲ Доход", callback_data="menu_income"),
        InlineKeyboardButton(text="▼ Расход", callback_data="menu_expense")
    )
    builder.row(InlineKeyboardButton(text="≡ Доп. меню", callback_data="menu_extra"))
    builder.row(InlineKeyboardButton(text="✕ Закрыть", callback_data="menu_close"))
    return builder.as_markup()

def get_extra_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="● Мой баланс", callback_data="extra_my_balance"),
        InlineKeyboardButton(text="○ Баланс всех", callback_data="extra_all_balance")
    )
    builder.row(
        InlineKeyboardButton(text="# Какой день?", callback_data="extra_day"),
        InlineKeyboardButton(text="↻ История", callback_data="extra_history")
    )
    builder.row(
        InlineKeyboardButton(text="★ События", callback_data="extra_events")
    )
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="menu_back_main"),
        InlineKeyboardButton(text="✕ Закрыть", callback_data="menu_close")
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
        
    builder.row(InlineKeyboardButton(text="← Отмена", callback_data="menu_cancel_action"))
    return builder.as_markup()

def get_events_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="+ Добавить", callback_data="event_add"))
    builder.row(
        InlineKeyboardButton(text="← Назад", callback_data="menu_back_main"),
        InlineKeyboardButton(text="✕ Закрыть", callback_data="menu_close")
    )
    return builder.as_markup()

def get_events_list_menu(page: int, total_pages: int):
    """Меню для списка событий с кнопками действий"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="<< Назад", callback_data=f"ev_page_{page - 1}"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперед >>", callback_data=f"ev_page_{page + 1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки действий
    builder.row(InlineKeyboardButton(text="+ Добавить", callback_data="event_add"))
    builder.row(
        InlineKeyboardButton(text="Редактировать", callback_data="event_edit_select"),
        InlineKeyboardButton(text="Удалить", callback_data="event_del_select")
    )
    builder.row(InlineKeyboardButton(text="<< В главное меню", callback_data="menu_back_main"))
    
    return builder.as_markup()

def get_events_select_menu(events, action: str):
    """Меню выбора события для редактирования или удаления"""
    builder = InlineKeyboardBuilder()
    
    for event in events:
        desc = event['description'][:25]
        callback_action = "ev_edit_date" if action == "edit" else "del_ev"
        builder.row(InlineKeyboardButton(
            text=f"{desc}",
            callback_data=f"{callback_action}_{str(event['_id'])}"
        ))
    
    builder.row(InlineKeyboardButton(text="<< Назад", callback_data="extra_events"))
    
    return builder.as_markup()

def get_event_edit_menu(event_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Изменить дату", callback_data=f"ev_edit_date_{event_id}"))
    builder.row(InlineKeyboardButton(text="Изменить описание", callback_data=f"ev_edit_desc_{event_id}"))
    builder.row(InlineKeyboardButton(text="Изменить периодичность", callback_data=f"ev_edit_rec_{event_id}"))
    builder.row(InlineKeyboardButton(text="<< Назад к списку", callback_data="extra_events"))
    return builder.as_markup()

def get_recurrence_menu(event_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="Ежегодно", callback_data=f"ev_set_rec_yearly_{event_id}"))
    builder.row(InlineKeyboardButton(text="Ежемесячно", callback_data=f"ev_set_rec_monthly_{event_id}"))
    builder.row(InlineKeyboardButton(text="Еженедельно", callback_data=f"ev_set_rec_weekly_{event_id}"))
    builder.row(InlineKeyboardButton(text="Без повторения", callback_data=f"ev_set_rec_none_{event_id}"))
    builder.row(InlineKeyboardButton(text="<< Отмена", callback_data=f"ev_manage_{event_id}"))
    return builder.as_markup()
