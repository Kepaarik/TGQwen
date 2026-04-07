from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from keyboards.inline_kb import get_events_menu, get_extra_menu, get_event_list_menu, get_event_edit_menu, get_recurrence_menu
from handlers.states import EventState, EditEventState
from database.events_db import get_all_events, add_event, get_event_by_id, update_event, delete_event
from services.date_utils import get_days_until, format_date_fancy
import asyncio

router = Router()

@router.callback_query(F.data == "extra_events")
async def show_events(callback: types.CallbackQuery):
    evs = await get_all_events()
    if not evs:
        text = "Список событий пуст."
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_events_menu())
    else:
        text = "<b>Управление событиями:</b>\nВыберите событие для редактирования или удаления:"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_event_list_menu(evs))
    await callback.answer()

@router.callback_query(F.data == "extra_events_list")
async def show_events_list(callback: types.CallbackQuery):
    evs = await get_all_events()
    if not evs:
        text = "Список событий пуст."
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_events_menu())
    else:
        text = "<b>Управление событиями:</b>\nВыберите событие для редактирования или удаления:"
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_event_list_menu(evs))
    await callback.answer()

@router.callback_query(F.data.startswith("ev_manage_"))
async def manage_event(callback: types.CallbackQuery):
    event_id = callback.data.replace("ev_manage_", "")
    event = await get_event_by_id(event_id)
    if not event:
        await callback.answer("Событие не найдено.", show_alert=True)
        return
    
    rec = event.get('recurrence', 'нет') or 'нет'
    text = (
        f"<b>📅 Событие:</b> {event['description']}\n"
        f"<b>Дата:</b> {event['date_str']}\n"
        f"<b>Периодичность:</b> {rec}\n"
        f"<b>Дней осталось:</b> {get_days_until(event['date_str']) or '—'}\n\n"
        f"Выберите действие:"
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_event_edit_menu(event_id))
    await callback.answer()

@router.callback_query(F.data.startswith("ev_edit_date_"))
async def start_edit_date(callback: types.CallbackQuery, state: FSMContext):
    event_id = callback.data.replace("ev_edit_date_", "")
    await state.update_data(event_id=event_id)
    await state.set_state(EditEventState.wait_new_date)
    await callback.message.edit_text("Введите новую дату события в формате ДД.ММ:")
    await callback.answer()

@router.message(EditEventState.wait_new_date, F.text)
async def process_new_date(message: types.Message, state: FSMContext):
    date_str = message.text.strip()
    if "." not in date_str:
        await message.answer("Ошибка: неправильный формат. Введите ДД.ММ:")
        return
    
    data = await state.get_data()
    event_id = data['event_id']
    await update_event(event_id, {"date_str": date_str})
    await message.answer("Дата обновлена!", reply_markup=get_event_edit_menu(event_id))
    await state.clear()

@router.callback_query(F.data.startswith("ev_edit_desc_"))
async def start_edit_desc(callback: types.CallbackQuery, state: FSMContext):
    event_id = callback.data.replace("ev_edit_desc_", "")
    await state.update_data(event_id=event_id)
    await state.set_state(EditEventState.wait_new_desc)
    await callback.message.edit_text("Введите новое описание события:")
    await callback.answer()

@router.message(EditEventState.wait_new_desc, F.text)
async def process_new_desc(message: types.Message, state: FSMContext):
    desc = message.text.strip()
    data = await state.get_data()
    event_id = data['event_id']
    await update_event(event_id, {"description": desc})
    await message.answer("Описание обновлено!", reply_markup=get_event_edit_menu(event_id))
    await state.clear()

@router.callback_query(F.data.startswith("ev_edit_rec_"))
async def start_edit_rec(callback: types.CallbackQuery):
    event_id = callback.data.replace("ev_edit_rec_", "")
    await callback.message.edit_text("Выберите новую периодичность:", reply_markup=get_recurrence_menu(event_id))
    await callback.answer()

@router.callback_query(F.data.startswith("ev_set_rec_"))
async def set_recurrence(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    # ev_set_rec_yearly_EVENTID
    rec_type = parts[4]  # yearly, monthly, weekly, none
    event_id = "_".join(parts[5:])  # на случай если в ID есть подчеркивания
    
    rec_map = {
        "yearly": "yearly",
        "monthly": "monthly",
        "weekly": "weekly",
        "none": None
    }
    
    rec_value = rec_map.get(rec_type)
    await update_event(event_id, {"recurrence": rec_value})
    
    rec_text = rec_value or "без повторения"
    await callback.message.edit_text(f"Периодичность изменена на: {rec_text}", reply_markup=get_event_edit_menu(event_id))
    await callback.answer()

@router.callback_query(F.data == "event_add")
async def start_add_event(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(EventState.wait_date)
    await callback.message.edit_text("Введите дату события в формате ДД.ММ (например, 31.12):")
    await callback.answer()

@router.message(EventState.wait_date, F.text)
async def process_event_date(message: types.Message, state: FSMContext):
    date_str = message.text.strip()
    if "." not in date_str:
        await message.answer("Ошибка: неправильный формат. Введите ДД.ММ:")
        return
        
    await state.update_data(date=date_str)
    await state.set_state(EventState.wait_desc)
    await message.answer("Введите описание события:")

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
    await callback.message.edit_text(f"Событие удалено.", reply_markup=get_events_menu())
    await callback.answer()
