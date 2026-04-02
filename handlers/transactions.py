from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from keyboards.inline_kb import get_currency_menu, get_main_menu
from handlers.states import TransactionState
from database.transactions import add_transaction
import asyncio
from services.finance_calc import get_personal_wallet_text

router = Router()

@router.callback_query(F.data.in_(["menu_income", "menu_expense"]))
async def start_transaction(callback: types.CallbackQuery, state: FSMContext):
    action_type = "income" if callback.data == "menu_income" else "expense"
    await state.update_data(type=action_type)
    await state.set_state(TransactionState.wait_currency)
    
    action_text = "Доход" if action_type == "income" else "Расход"
    await callback.message.edit_text(f"Выберите валюту ({action_text}):", reply_markup=get_currency_menu())
    await callback.answer()

@router.callback_query(TransactionState.wait_currency, F.data.startswith("set_curr_"))
async def process_currency(callback: types.CallbackQuery, state: FSMContext):
    currency = callback.data.replace("set_curr_", "")
    await state.update_data(currency=currency)
    await state.set_state(TransactionState.wait_amount)
    
    data = await state.get_data()
    action_type = data['type']
    
    type_label = "Пополнение" if action_type == "income" else "Снятие"
    text = f"<b>{type_label} ({currency})</b>\n\nВведите сумму:"
    
    req_msg = await callback.message.edit_text(text, parse_mode="HTML")
    await state.update_data(req_msg_id=req_msg.message_id) # Save message ID to delete later like in TGQwen
    await callback.answer()

@router.message(TransactionState.wait_amount, F.text)
async def process_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    action_type = data['type']
    currency = data['currency']
    req_msg_id = data.get('req_msg_id')
    
    # Delete user's message
    try:
        await message.delete()
    except:
        pass
        
    # Delete request message
    if req_msg_id:
        try:
            await message.bot.delete_message(chat_id=message.chat.id, message_id=req_msg_id)
        except:
            pass

    try:
        clean_input = message.text.replace(',', '.').strip()
        amount = float(clean_input)
        if amount <= 0:
            raise ValueError
    except ValueError:
        err = await message.answer("Ошибка: Введите корректное положительное число.")
        await asyncio.sleep(2)
        try:
            await err.delete()
        except:
            pass
        await state.clear()
        text = await get_personal_wallet_text(message.from_user.id)
        await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")
        return

    is_income = action_type == "income"
    await add_transaction(message.from_user.id, message.from_user.first_name, amount, currency, is_income)
    
    type_str = "внесен" if is_income else "снят"
    success_msg = await message.answer(f"Успешно: {amount:.2f} {currency} {type_str}.")
    
    await state.clear()
    await asyncio.sleep(2)
    try:
        await success_msg.delete()
    except:
        pass
        
    text = await get_personal_wallet_text(message.from_user.id)
    await message.answer(text, reply_markup=get_main_menu(), parse_mode="HTML")
