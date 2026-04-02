import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramForbiddenError

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = '8788194731:AAGKYQ6ur_aR5sh4INVRqSNNl8f_I3dXLfs'
PORT = int(os.getenv('PORT', 8080))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- НАСТРОЙКИ ВАЛЮТ ---
AVAILABLE_CURRENCIES = ['BYN', 'USD', 'EUR', 'CNY']

CURRENCY_SYMBOLS = {
    'BYN': 'Br',
    'USD': '$',
    'EUR': '€',
    'CNY': '¥'
}

# --- ХРАНИЛИЩЕ ДАННЫХ ---
users_db = {}

def get_user_data(user_id: int):
    if user_id not in users_db:
        users_db[user_id] = {
            'balances': {
                'BYN': 0.0,
                'USD': 0.0,
                'EUR': 0.0,
                'CNY': 0.0
            },
            'active_currency': 'BYN',
            'state': 'IDLE',
            'wallet_msg_id': None,
            'temp_req_msg_id': None # ID сообщения с запросом ввода
        }
    return users_db[user_id]

def set_state(user_id: int, state: str):
    data = get_user_data(user_id)
    data['state'] = state

# --- КЛАВИАТУРЫ ---

def get_wallet_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Пополнить", callback_data="action_deposit"),
        InlineKeyboardButton(text="➖ Снять", callback_data="action_withdraw")
    )
    builder.row(InlineKeyboardButton(text="💱 Сменить активную", callback_data="action_currency"))
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="action_close"))
    return builder.as_markup()

def get_currency_keyboard(active_curr: str):
    builder = InlineKeyboardBuilder()
    rows = []
    for i in range(0, len(AVAILABLE_CURRENCIES), 2):
        row = []
        for curr in AVAILABLE_CURRENCIES[i:i+2]:
            symbol = CURRENCY_SYMBOLS[curr]
            label = f"✅ {curr} ({symbol})" if curr == active_curr else f"{curr} ({symbol})"
            row.append(InlineKeyboardButton(text=label, callback_data=f"set_curr_{curr}"))
        rows.append(row)
    
    for row in rows:
        builder.row(*row)
        
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="action_back_to_wallet"))
    return builder.as_markup()

# --- БЕЗОПАСНЫЕ ФУНКЦИИ ---

async def safe_send_message(chat_id, text, **kwargs):
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except TelegramForbiddenError:
        pass
    except Exception as e:
        logging.error(f"Send error: {e}")
    return None

async def safe_edit_message(chat_id, message_id, text, **kwargs):
    try:
        return await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, **kwargs)
    except TelegramForbiddenError:
        pass
    except Exception as e:
        logging.error(f"Edit error: {e}")
    return None

async def safe_delete_message(chat_id, message_id):
    try:
        if message_id:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except:
        pass

# --- ЛОГИКА ОТОБРАЖЕНИЯ ---

async def show_wallet_menu(message: types.Message | types.CallbackQuery, hide_old: bool = False):
    """Показывает главное меню со всеми балансами"""
    user_id = message.from_user.id
    data = get_user_data(user_id)
    active = data['active_currency']
    active_symbol = CURRENCY_SYMBOLS[active]
    
    balances_text = ""
    for curr in AVAILABLE_CURRENCIES:
        symbol = CURRENCY_SYMBOLS[curr]
        bal = data['balances'][curr]
        if curr == active:
            balances_text += f"🔹 <b>{curr}: {bal:.2f} {symbol}</b> (Активна)\n"
        else:
            balances_text += f"⚪️ {curr}: {bal:.2f} {symbol}\n"
    
    text = (
        f"💳 <b>Мультивалютный Кошелек</b>\n\n"
        f"{balances_text}\n"
        f"Операции проводятся в <b>{active} {active_symbol}</b>."
    )
    
    kb = get_wallet_keyboard()
    
    if isinstance(message, types.CallbackQuery):
        if hide_old:
            try:
                await message.message.delete()
                data['wallet_msg_id'] = None
            except:
                pass
            return

        await safe_edit_message(
            chat_id=message.message.chat.id,
            message_id=message.message.message_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        data['wallet_msg_id'] = message.message.message_id
    else:
        await safe_delete_message(message.chat.id, message.message_id)
        
        sent_msg = await safe_send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )
        if sent_msg:
            data['wallet_msg_id'] = sent_msg.message_id

async def show_currency_menu(callback: types.CallbackQuery):
    data = get_user_data(callback.from_user.id)
    text = "💱 <b>Выберите активную валюту:</b>"
    await safe_edit_message(
        chat_id=callback.message.chat.id,
        message_id=callback.message.message_id,
        text=text,
        reply_markup=get_currency_keyboard(data['active_currency']),
        parse_mode="HTML"
    )

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    set_state(message.from_user.id, 'IDLE')
    await show_wallet_menu(message)

@dp.callback_query(F.data.startswith("action_") | F.data.startswith("set_curr_"))
async def handle_callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = get_user_data(user_id)
    action = callback.data

    if action == "action_close":
        await safe_delete_message(callback.message.chat.id, callback.message.message_id)
        await callback.answer()
        return

    if action == "action_back_to_wallet":
        set_state(user_id, 'IDLE')
        await show_wallet_menu(callback)
        await callback.answer()
        return

    if action == "action_currency":
        await show_currency_menu(callback)
        await callback.answer()
        return

    if action.startswith("set_curr_"):
        new_curr = action.replace("set_curr_", "")
        data['active_currency'] = new_curr
        await callback.answer(f"Активная валюта: {new_curr}")
        await show_wallet_menu(callback)
        return

    # ПОПОЛНЕНИЕ
    if action == "action_deposit":
        set_state(user_id, 'DEPOSIT')
        await show_wallet_menu(callback, hide_old=True) 
        
        curr = data['active_currency']
        symbol = CURRENCY_SYMBOLS[curr]
        req_msg = await safe_send_message(
            chat_id=callback.message.chat.id,
            text=f"💸 <b>Пополнение счета {curr}</b>\n\nВведите сумму в {symbol}:",
            reply_markup=ForceReply(input_field_placeholder=f"Сумма в {symbol}"),
            parse_mode="HTML"
        )
        # Сохраняем ID сообщения с запросом, чтобы потом удалить его
        if req_msg:
            data['temp_req_msg_id'] = req_msg.message_id
            
        await callback.answer()
        return

    # СНЯТИЕ
    if action == "action_withdraw":
        curr = data['active_currency']
        if data['balances'][curr] <= 0:
            await callback.answer(f"⚠️ Счет {curr} пуст!", show_alert=True)
            return
        
        set_state(user_id, 'WITHDRAW')
        await show_wallet_menu(callback, hide_old=True)

        symbol = CURRENCY_SYMBOLS[curr]
        req_msg = await safe_send_message(
            chat_id=callback.message.chat.id,
            text=f"💸 <b>Снятие со счета {curr}</b>\n\nДоступно: {data['balances'][curr]:.2f} {symbol}\nВведите сумму:",
            reply_markup=ForceReply(input_field_placeholder=f"Сумма в {symbol}"),
            parse_mode="HTML"
        )
        # Сохраняем ID сообщения с запросом
        if req_msg:
            data['temp_req_msg_id'] = req_msg.message_id

        await callback.answer()
        return

@dp.message(F.text)
async def handle_text_input(message: types.Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    state = data['state']

    if state == 'IDLE':
        return 

    # 1. Удаляем ввод пользователя (число)
    await safe_delete_message(message.chat.id, message.message_id)
    
    # 2. Удаляем сообщение с запросом ввода ("Введите сумму..."), если оно есть
    if data.get('temp_req_msg_id'):
        await safe_delete_message(message.chat.id, data['temp_req_msg_id'])
        data['temp_req_msg_id'] = None # Сбрасываем ID

    try:
        clean_input = message.text.replace(',', '.').strip()
        amount = float(clean_input)
        if amount <= 0:
            raise ValueError
    except ValueError:
        err = await safe_send_message(chat_id=message.chat.id, text="❌ Введите корректное положительное число")
        if err:
            await asyncio.sleep(2)
            await safe_delete_message(err.chat.id, err.message_id)
        set_state(user_id, 'IDLE')
        await show_wallet_menu(message) 
        return

    curr = data['active_currency']
    symbol = CURRENCY_SYMBOLS[curr]

    if state == 'DEPOSIT':
        data['balances'][curr] += amount
        set_state(user_id, 'IDLE')
        
        success = await safe_send_message(chat_id=message.chat.id, text=f"✅ Счет {curr} пополнен на {amount:.2f} {symbol}")
        if success:
            await asyncio.sleep(2)
            await safe_delete_message(success.chat.id, success.message_id)
        
        await show_wallet_menu(message)

    elif state == 'WITHDRAW':
        if amount > data['balances'][curr]:
            err = await safe_send_message(chat_id=message.chat.id, text=f"❌ Недостаточно средств на счете {curr}. Баланс: {data['balances'][curr]:.2f} {symbol}")
            if err:
                await asyncio.sleep(2)
                await safe_delete_message(err.chat.id, err.message_id)
            await show_wallet_menu(message)
            return
            
        data['balances'][curr] -= amount
        set_state(user_id, 'IDLE')
        
        success = await safe_send_message(chat_id=message.chat.id, text=f"✅ Со счета {curr} снято {amount:.2f} {symbol}")
        if success:
            await asyncio.sleep(2)
            await safe_delete_message(success.chat.id, success.message_id)
            
        await show_wallet_menu(message)

# --- ФИКТИВНЫЙ СЕРВЕР ДЛЯ RENDER ---
async def handle_request(request):
    return web.Response(text="Bot is running")

async def start_fake_server():
    app = web.Application()
    app.router.add_get('/', handle_request)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', PORT)
    await site.start()
    print(f"Server on port {PORT}")

async def main():
    asyncio.create_task(start_fake_server())
    print("Bot started...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())