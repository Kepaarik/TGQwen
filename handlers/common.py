import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from keyboards.inline_kb import get_main_menu, get_extra_menu
from aiogram.fsm.context import FSMContext

router = Router()

async def ensure_clean_state(message_or_call, state: FSMContext):
    await state.clear()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await ensure_clean_state(message, state)
    await message.answer("Главное меню:", reply_markup=get_main_menu())

@router.callback_query(F.data == "menu_back_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await ensure_clean_state(callback, state)
    try:
        await callback.message.edit_text("Главное меню:", reply_markup=get_main_menu())
    except:
        await callback.message.answer("Главное меню:", reply_markup=get_main_menu())
    await callback.answer()

@router.callback_query(F.data == "menu_extra")
async def show_extra_menu(callback: types.CallbackQuery, state: FSMContext):
    await ensure_clean_state(callback, state)
    await callback.message.edit_text("Дополнительно:", reply_markup=get_extra_menu())
    await callback.answer()

@router.callback_query(F.data == "menu_cancel_action")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await ensure_clean_state(callback, state)
    await callback.message.edit_text("Действие отменено. Главное меню:", reply_markup=get_main_menu())
    await callback.answer("Отменено")
