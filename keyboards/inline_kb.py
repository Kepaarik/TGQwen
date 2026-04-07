from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from config import AVAILABLE_CURRENCIES

def get_main_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="\u25B2 Доход", callback_data="menu_income"),
        InlineKeyboardButton(text="\u25BC Расход", callback_data="menu_expense")
    )
    builder.row(InlineKeyboardButton(text="\u2261 Доп. меню", callback_data="menu_extra"))
    builder.row(InlineKeyboardButton(text="\u2718 Закрыть", callback_data="menu_close"))
    return builder.as_markup()

def get_extra_menu():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="\u25CF Мой баланс", callback_data="extra_my_balance"),
        InlineKeyboardButton(text="\u25CB Баланс всех", callback_data="extra_all_balance")
    )
    builder.row(
        InlineKeyboardButton(text="# Какой день?", callback_data="extra_day"),
        InlineKeyboardButton(text="\u21BB История", callback_data="extra_history")
    )
    builder.row(
        InlineKeyboardButton(text="\u2605 События", callback_data="extra_events")
    )
    builder.row(
        InlineKeyboardButton(text="\u2190 Назад", callback_data="menu_back_main"),
        InlineKeyboardButton(text="\u2718 Закрыть", callback_data="menu_close")
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
        
    builder.row(InlineKeyboardButton(text="\u2190 Отмена", callback_data="menu_cancel_action"))
    return builder.as_markup()

def get_events_menu():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="+ Добавить", callback_data="event_add"))
    builder.row(
        InlineKeyboardButton(text="\u2190 Назад", callback_data="menu_back_main"),
        InlineKeyboardButton(text="\u2718 Закрыть", callback_data="menu_close")
    )
    return builder.as_markup()

def get_events_list_menu(page: int, total_pages: int):
    """Меню для списка событий с кнопками действий"""
    builder = InlineKeyboardBuilder()
    
    # Кнопки пагинации
    nav_buttons = []
    if page > 0:
        nav_buttons.append(InlineKeyboardButton(text="\u2190 Назад", callback_data=f"ev_page_{page - 1}"))
    
    if page < total_pages - 1:
        nav_buttons.append(InlineKeyboardButton(text="Вперед \u2192", callback_data=f"ev_page_{page + 1}"))
    
    if nav_buttons:
        builder.row(*nav_buttons)
    
    # Кнопки действий
    builder.row(InlineKeyboardButton(text="+ Добавить", callback_data="event_add"))
    builder.row(
        InlineKeyboardButton(text="\u270E Редактировать", callback_data="event_edit_select"),
        InlineKeyboardButton(text="\u2718 Удалить", callback_data="event_del_select")
    )
    builder.row(InlineKeyboardButton(text="\u2190 В главное меню", callback_data="menu_back_main"))
    
    return builder.as_markup()

def get_events_select_menu(events, action: str):
    """Меню выбора события для редактирования или удаления"""
    builder = InlineKeyboardBuilder()
    
    for event in events:
        desc = event['description'][:25]
        if action == "edit":
            # Для редактирования передаем ID события в меню выбора параметра
            callback_action = "ev_select_edit"
        else:
            callback_action = "del_ev"
        builder.row(InlineKeyboardButton(
            text=f"{desc}",
            callback_data=f"{callback_action}_{str(event['_id'])}"
        ))
    
    builder.row(InlineKeyboardButton(text="\u2190 Назад", callback_data="extra_events"))
    
    return builder.as_markup()

def get_event_edit_menu(event_id):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="\u270E Изменить дату", callback_data=f"ev_edit_date_{event_id}"))
    builder.row(InlineKeyboardButton(text="\u270E Изменить описание", callback_data=f"ev_edit_desc_{event_id}"))
    builder.row(InlineKeyboardButton(text="\u270E Изменить периодичность", callback_data=f"ev_edit_rec_{event_id}"))
    builder.row(InlineKeyboardButton(text="\u2190 Отмена", callback_data="extra_events"))
    return builder.as_markup()

def get_recurrence_menu(event_id, current_rec):
    builder = InlineKeyboardBuilder()
    rec_symbol = {'yearly': '\U0001F4C5', 'monthly': '\U0001F5D3', 'weekly': '\U0001F4C6', None: '\u221E'}.get(current_rec, '\u221E')
    builder.row(InlineKeyboardButton(text=f"\U0001F4C5 Ежегодно {('✓' if current_rec == 'yearly' else '')}", callback_data=f"ev_set_rec_yearly_{event_id}"))
    builder.row(InlineKeyboardButton(text=f"\U0001F5D3 Ежемесячно {('✓' if current_rec == 'monthly' else '')}", callback_data=f"ev_set_rec_monthly_{event_id}"))
    builder.row(InlineKeyboardButton(text=f"\U0001F4C6 Еженедельно {('✓' if current_rec == 'weekly' else '')}", callback_data=f"ev_set_rec_weekly_{event_id}"))
    builder.row(InlineKeyboardButton(text=f"\u221E Без повторения {('✓' if current_rec is None else '')}", callback_data=f"ev_set_rec_none_{event_id}"))
    builder.row(InlineKeyboardButton(text="\u2190 Отмена", callback_data=f"ev_manage_{event_id}"))
    return builder.as_markup()

def get_cancel_keyboard(callback_data: str = "extra_events"):
    """Клавиатура с кнопкой отмены/назад"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="\u2190 Отмена", callback_data=callback_data))
    return builder.as_markup()
