import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from keyboards.inline_kb import get_main_menu, get_extra_menu
from aiogram.fsm.context import FSMContext
from services.finance_calc import get_personal_wallet_text, format_balance_tree

router = Router()

async def ensure_clean_state(message_or_call, state: FSMContext):
    await state.clear()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await ensure_clean_state(message, state)
    try:
        await message.delete()
    except:
        pass
    text = await get_personal_wallet_text(message.from_user.id)
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")

@router.callback_query(F.data == "menu_back_main")
async def back_to_main(callback: types.CallbackQuery, state: FSMContext):
    await ensure_clean_state(callback, state)
    text = await get_personal_wallet_text(callback.from_user.id)
    try:
        await callback.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="HTML")
    except Exception as e:
        logging.warning(f"Не удалось отредактировать сообщение: {e}")
        try:
            await callback.message.delete()
        except:
            pass
        await callback.message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "menu_extra")
async def show_extra_menu(callback: types.CallbackQuery, state: FSMContext):
    await ensure_clean_state(callback, state)
    await callback.message.edit_text("Дополнительно:", reply_markup=get_extra_menu())
    await callback.answer()

@router.callback_query(F.data == "menu_cancel_action")
async def cancel_action(callback: types.CallbackQuery, state: FSMContext):
    await ensure_clean_state(callback, state)
    text = await get_personal_wallet_text(callback.from_user.id)
    await callback.message.edit_text(text, reply_markup=get_main_menu(), parse_mode="HTML")
    await callback.answer("Отменено")

@router.callback_query(F.data == "menu_close")
async def close_menu(callback: types.CallbackQuery, state: FSMContext):
    await ensure_clean_state(callback, state)
    try:
        await callback.message.delete()
    except:
        pass
    await callback.answer()
