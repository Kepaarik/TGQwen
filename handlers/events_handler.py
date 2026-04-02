from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from keyboards.inline_kb import get_events_menu, get_extra_menu
from handlers.states import EventState
from database.events_db import get_all_events, add_event
from services.date_utils import get_days_until, format_date_fancy
import asyncio

router = Router()

@router.callback_query(F.data == "extra_events")
async def show_events(callback: types.CallbackQuery):
    evs = await get_all_events()
    if not evs:
        text = "Список событий пуст."
    else:
        res = ["<b>Ближайшие события:</b>\n"]
        for e in evs:
            days_left = get_days_until(e['date_str'])
            res.append(f"<b>{format_date_fancy(e['date_str'])}</b>: {e['description']}\n   └ <i>{days_left or ''}</i>")
        text = "\n\n".join(res)
        
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_events_menu())
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
