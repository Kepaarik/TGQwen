from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from keyboards.inline_kb import get_events_menu, get_extra_menu, get_events_list_menu, get_events_select_menu, get_event_edit_menu, get_recurrence_menu, get_cancel_keyboard
from handlers.states import EventState, EditEventState
from database.events_db import get_all_events, add_event, get_event_by_id, update_event, delete_event
from services.date_utils import get_days_until, format_date_fancy
import asyncio

router = Router()

EVENTS_PER_PAGE = 5

async def show_events_page(callback: types.CallbackQuery, page: int = 0):
    """Показать страницу списка событий с кнопками действий"""
    evs = await get_all_events()
    
    if not evs:
        text = "<b>Список событий:</b>\n\nСписок событий пуст."
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_events_menu())
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=get_events_menu())
        return
    
    total_pages = (len(evs) + EVENTS_PER_PAGE - 1) // EVENTS_PER_PAGE
    
    start_idx = page * EVENTS_PER_PAGE
    end_idx = min(start_idx + EVENTS_PER_PAGE, len(evs))
    page_events = evs[start_idx:end_idx]
    
    text = "<b>Список событий:</b>\n\n"
    for i, event in enumerate(page_events, start=start_idx + 1):
        rec = event.get('recurrence', 'нет') or 'нет'
        days_left = get_days_until(event['date_str'], rec)
        # Символы периодичности
        rec_symbol = {'yearly': '\U0001F4C5', 'monthly': '\U0001F5D3', 'weekly': '\U0001F4C6', 'нет': '\u221E', None: '\u221E'}.get(rec, '\u221E')
        text += f"<b>{i}.</b> {event['description']}\n"
        text += f"   \U0001F4C5 Дата: {event['date_str']} | Периодичность: {rec_symbol} {rec}\n"
        if rec != 'нет' and rec is not None and days_left:
            text += f"   \u231B Дней осталось: {days_left}\n"
        text += "\n"
    
    try:
        await callback.message.edit_text(
            text, 
            parse_mode="HTML", 
            reply_markup=get_events_list_menu(page, total_pages)
        )
    except Exception as e:
        # Если редактирование не удалось, отправляем новое сообщение
        await callback.message.answer(
            text, 
            parse_mode="HTML", 
            reply_markup=get_events_list_menu(page, total_pages)
        )

@router.callback_query(F.data == "extra_events")
async def show_events(callback: types.CallbackQuery):
    await show_events_page(callback, page=0)
    await callback.answer()

@router.callback_query(F.data == "extra_events_list")
async def show_events_list(callback: types.CallbackQuery):
    await show_events_page(callback, page=0)
    await callback.answer()

@router.callback_query(F.data.startswith("ev_page_"))
async def paginate_events(callback: types.CallbackQuery):
    page = int(callback.data.replace("ev_page_", ""))
    await show_events_page(callback, page=page)
    await callback.answer()

@router.callback_query(F.data == "event_edit_select")
async def select_event_to_edit(callback: types.CallbackQuery):
    evs = await get_all_events()
    if not evs:
        await callback.answer("Нет событий для редактирования.", show_alert=True)
        return
    
    text = "<b>✏️ Выберите событие для редактирования:</b>\n\n"
    for i, event in enumerate(evs, start=1):
        text += f"<b>{i}.</b> {event['description']} ({event['date_str']})\n"
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_events_select_menu(evs, "edit"))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_events_select_menu(evs, "edit"))
    await callback.answer()

@router.callback_query(F.data == "event_del_select")
async def select_event_to_delete(callback: types.CallbackQuery):
    evs = await get_all_events()
    if not evs:
        await callback.answer("Нет событий для удаления.", show_alert=True)
        return
    
    text = "<b>🗑️ Выберите событие для удаления:</b>\n\n"
    for i, event in enumerate(evs, start=1):
        text += f"<b>{i}.</b> {event['description']} ({event['date_str']})\n"
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_events_select_menu(evs, "del"))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_events_select_menu(evs, "del"))
    await callback.answer()

@router.callback_query(F.data.startswith("ev_select_edit_"))
async def show_edit_options(callback: types.CallbackQuery):
    """Показать меню выбора параметра для редактирования после выбора события"""
    event_id = callback.data.replace("ev_select_edit_", "")
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return
    
    current_date = event.get('date_str', 'не указана')
    current_desc = event.get('description', 'не указано')
    current_rec = event.get('recurrence', None) or 'нет'
    rec_text = {'yearly': 'Ежегодно', 'monthly': 'Ежемесячно', 'weekly': 'Еженедельно', 'нет': 'Без повторения', None: 'Без повторения'}.get(current_rec, 'Без повторения')
    
    text = f"<b>✏️ Редактирование события:</b>\n\n"
    text += f"<b>Описание:</b> {current_desc}\n"
    text += f"<b>Дата:</b> {current_date}\n"
    text += f"<b>Периодичность:</b> {rec_text}\n\n"
    text += "Выберите параметр для изменения:"
    
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    await callback.answer()

@router.callback_query(F.data.startswith("ev_edit_date_"))
async def start_edit_date(callback: types.CallbackQuery, state: FSMContext):
    event_id = callback.data.replace("ev_edit_date_", "")
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return
    
    current_date = event.get('date_str', 'не указана')
    await state.update_data(event_id=event_id, old_message_id=callback.message.message_id)
    await state.set_state(EditEventState.wait_new_date)
    
    text = f"<b>Редактирование даты:</b>\n\nТекущая дата: {current_date}\n\nВведите новую дату события в формате ДД.ММ:"
    try:
        msg = await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_keyboard(f"ev_manage_{event_id}"))
        await state.update_data(event_id=event_id, old_message_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard(f"ev_manage_{event_id}"))
        await state.update_data(event_id=event_id, old_message_id=msg.message_id)
    await callback.answer()

@router.message(EditEventState.wait_new_date, F.text)
async def process_new_date(message: types.Message, state: FSMContext):
    date_str = message.text.strip()
    if "." not in date_str:
        await message.answer("Ошибка: неправильный формат. Введите ДД.ММ:")
        return
    
    data = await state.get_data()
    event_id = data['event_id']
    old_message_id = data.get('old_message_id')
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception:
        pass
    
    await update_event(event_id, {"date_str": date_str})
    
    # Возвращаемся к меню редактирования события
    text = f"<b>Дата обновлена!</b>\n\nНовая дата: {date_str}"
    try:
        await message.answer(text, parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    except Exception:
        await message.answer(text, parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    await state.clear()

@router.callback_query(F.data.startswith("ev_edit_desc_"))
async def start_edit_desc(callback: types.CallbackQuery, state: FSMContext):
    event_id = callback.data.replace("ev_edit_desc_", "")
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return
    
    current_desc = event.get('description', 'не указано')
    await state.update_data(event_id=event_id, old_message_id=callback.message.message_id)
    await state.set_state(EditEventState.wait_new_desc)
    
    text = f"<b>Редактирование описания:</b>\n\nТекущее описание: {current_desc}\n\nВведите новое описание события:"
    try:
        msg = await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_keyboard(f"ev_manage_{event_id}"))
        await state.update_data(event_id=event_id, old_message_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard(f"ev_manage_{event_id}"))
        await state.update_data(event_id=event_id, old_message_id=msg.message_id)
    await callback.answer()

@router.message(EditEventState.wait_new_desc, F.text)
async def process_new_desc(message: types.Message, state: FSMContext):
    desc = message.text.strip()
    data = await state.get_data()
    event_id = data['event_id']
    
    # Удаляем сообщение пользователя
    try:
        await message.delete()
    except Exception:
        pass
    
    await update_event(event_id, {"description": desc})
    
    # Возвращаемся к меню редактирования события
    text = f"<b>Описание обновлено!</b>\n\nНовое описание: {desc}"
    try:
        await message.answer(text, parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    except Exception:
        await message.answer(text, parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    await state.clear()

@router.callback_query(F.data.startswith("ev_edit_rec_"))
async def start_edit_rec(callback: types.CallbackQuery):
    event_id = callback.data.replace("ev_edit_rec_", "")
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return
    
    current_rec = event.get('recurrence', None) or 'нет'
    rec_text = {'yearly': 'Ежегодно', 'monthly': 'Ежемесячно', 'weekly': 'Еженедельно', 'нет': 'Без повторения', None: 'Без повторения'}.get(current_rec, 'Без повторения')
    
    text = f"<b>Редактирование периодичности:</b>\n\nТекущая периодичность: {rec_text}\n\nВыберите новую периодичность:"
    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_recurrence_menu(event_id, current_rec))
    except Exception:
        await callback.message.answer(text, parse_mode="HTML", reply_markup=get_recurrence_menu(event_id, current_rec))
    await callback.answer()

@router.callback_query(F.data.startswith("ev_set_rec_"))
async def set_recurrence(callback: types.CallbackQuery):
    # Формат: ev_set_rec_TYPE_EVENTID
    # Находим второй подчеркивание после ev_set_rec
    prefix = "ev_set_rec_"
    if not callback.data.startswith(prefix):
        await callback.answer("Ошибка формата", show_alert=True)
        return
    
    rest = callback.data[len(prefix):]
    # rest = "yearly_EVENTID" или "none_EVENTID"
    underscore_pos = rest.find("_")
    if underscore_pos == -1:
        await callback.answer("Ошибка формата", show_alert=True)
        return
    
    rec_type = rest[:underscore_pos]
    event_id = rest[underscore_pos + 1:]
    
    rec_map = {
        "yearly": "yearly",
        "monthly": "monthly",
        "weekly": "weekly",
        "none": None
    }
    
    rec_value = rec_map.get(rec_type)
    await update_event(event_id, {"recurrence": rec_value})
    
    rec_text_map = {
        "yearly": "Ежегодно",
        "monthly": "Ежемесячно",
        "weekly": "Еженедельно",
        "none": "Без повторения"
    }
    rec_text = rec_text_map.get(rec_type, "Без повторения")
    
    # Получаем обновленное событие для возврата к меню редактирования
    event = await get_event_by_id(event_id)
    if event:
        current_date = event.get('date_str', 'не указана')
        current_desc = event.get('description', 'не указано')
        current_rec = event.get('recurrence', None) or 'нет'
        rec_display = {'yearly': 'Ежегодно', 'monthly': 'Ежемесячно', 'weekly': 'Еженедельно', 'нет': 'Без повторения', None: 'Без повторения'}.get(current_rec, 'Без повторения')
        
        text = f"<b>✏️ Редактирование события:</b>\n\n"
        text += f"<b>Описание:</b> {current_desc}\n"
        text += f"<b>Дата:</b> {current_date}\n"
        text += f"<b>Периодичность:</b> {rec_display}\n\n"
        text += "Выберите параметр для изменения:"
        
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_event_edit_menu(str(event['_id'])))
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=get_event_edit_menu(str(event['_id'])))
    else:
        try:
            await callback.message.edit_text(f"Периодичность изменена на: {rec_text}", reply_markup=get_events_menu())
        except Exception:
            await callback.message.answer(f"Периодичность изменена на: {rec_text}", reply_markup=get_events_menu())
    
    await callback.answer()

@router.callback_query(F.data.startswith("ev_manage_"))
async def back_to_edit_menu(callback: types.CallbackQuery):
    event_id = callback.data.replace("ev_manage_", "")
    try:
        await callback.message.edit_text("<b>Редактирование события:</b>\n\nВыберите параметр для изменения:", parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    except Exception:
        await callback.message.answer("<b>Редактирование события:</b>\n\nВыберите параметр для изменения:", parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    await callback.answer()

@router.callback_query(F.data == "event_add")
async def start_add_event(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(EventState.wait_date)
    await callback.message.edit_text("Введите дату события в формате ДД.ММ (например, 31.12):", reply_markup=get_cancel_keyboard("extra_events"))
    await callback.answer()

@router.message(EventState.wait_date, F.text)
async def process_event_date(message: types.Message, state: FSMContext):
    date_str = message.text.strip()
    if "." not in date_str:
        await message.answer("Ошибка: неправильный формат. Введите ДД.ММ:", reply_markup=get_cancel_keyboard("extra_events"))
        return
        
    await state.update_data(date=date_str)
    await state.set_state(EventState.wait_desc)
    await message.answer("Введите описание события:", reply_markup=get_cancel_keyboard("extra_events"))

@router.message(EventState.wait_desc, F.text)
async def process_event_desc(message: types.Message, state: FSMContext):
    data = await state.get_data()
    date_str = data['date']
    desc = message.text.strip()
    
    await add_event(message.from_user.id, message.from_user.first_name, date_str, desc, "yearly")
    await message.answer("Событие успешно добавлено!", reply_markup=get_events_menu())
    await state.clear()

from aiogram.filters import Command
from config import ADMIN_ID
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

@router.message(Command("delevent"))
async def admin_del_event(message: types.Message):
    if ADMIN_ID != 0 and message.from_user.id != ADMIN_ID:
        return
        
    evs = await get_all_events()
    if not evs:
        await message.answer("Нет событий для удаления.")
        return
        
    builder = InlineKeyboardBuilder()
    for e in evs[:10]:
        builder.row(InlineKeyboardButton(text=f"✕ {e['description'][:25]}", callback_data=f"del_ev_{str(e['_id'])}"))
    builder.row(InlineKeyboardButton(text="✕ Закрыть", callback_data="menu_close"))
    
    await message.answer("Выберите событие для удаления:", reply_markup=builder.as_markup())

@router.callback_query(F.data.startswith("del_ev_"))
async def process_del_event(callback: types.CallbackQuery):
    if ADMIN_ID != 0 and callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет прав.", show_alert=True)
        return
        
    event_id = callback.data.replace("del_ev_", "")
    await delete_event(event_id)
    
    # Возвращаемся к списку событий для выбора удаления
    evs = await get_all_events()
    if not evs:
        text = "<b>🗑️ Выберите событие для удаления:</b>\n\nНет событий для удаления."
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_events_menu())
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=get_events_menu())
    else:
        text = "<b>🗑️ Выберите событие для удаления:</b>\n\n"
        for i, event in enumerate(evs, start=1):
            text += f"<b>{i}.</b> {event['description']} ({event['date_str']})\n"
        try:
            await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_events_select_menu(evs, "del"))
        except Exception:
            await callback.message.answer(text, parse_mode="HTML", reply_markup=get_events_select_menu(evs, "del"))
    
    await callback.answer()
