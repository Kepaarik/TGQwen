import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.exceptions import TelegramForbiddenError, TelegramAPIError

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = '8788194731:AAGKYQ6ur_aR5sh4INVRqSNNl8f_I3dXLfs'  # Лучше брать из env
PORT = int(os.getenv('PORT', 8080))

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ХРАНИЛИЩЕ ДАННЫХ ---
users_db = {}

def get_user_data(user_id: int):
    if user_id not in users_db:
        users_db[user_id] = {'balance': 0.0, 'state': 'IDLE', 'last_wallet_msg_id': None}
    return users_db[user_id]

def update_balance(user_id: int, amount: float):
    data = get_user_data(user_id)
    data['balance'] += amount

def set_state(user_id: int, state: str):
    data = get_user_data(user_id)
    data['state'] = state

# --- КЛАВИАТУРЫ ---
def get_wallet_keyboard():
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Пополнить баланс", callback_data="action_deposit"),
        InlineKeyboardButton(text="➖ Снять средства", callback_data="action_withdraw")
    )
    builder.row(InlineKeyboardButton(text="❌ Закрыть меню", callback_data="action_close"))
    return builder.as_markup()

# --- ФУНКЦИИ ОТОБРАЖЕНИЯ С ОБРАБОТКОЙ ОШИБОК ---

async def safe_send_message(chat_id, text, **kwargs):
    """Отправляет сообщение, игнорируя ошибки Forbidden"""
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except TelegramForbiddenError:
        logging.warning(f"Bot was kicked from chat {chat_id}. Ignoring.")
    except Exception as e:
        logging.error(f"Error sending message to {chat_id}: {e}")
    return None

async def safe_edit_message(chat_id, message_id, text, **kwargs):
    """Редактирует сообщение, игнорируя ошибки Forbidden"""
    try:
        return await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, **kwargs)
    except TelegramForbiddenError:
        logging.warning(f"Bot was kicked from chat {chat_id}. Ignoring edit.")
    except Exception as e:
        logging.error(f"Error editing message in {chat_id}: {e}")
    return None

async def render_wallet(message: types.Message | types.CallbackQuery, edit: bool = True):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    
    text = (
        f"💳 <b>Личный Кошелек</b>\n\n"
        f"Текущий баланс: <b>{data['balance']:.2f} RUB</b>\n\n"
        f"Выберите действие:"
    )
    
    if isinstance(message, types.CallbackQuery):
        if edit:
            await safe_edit_message(
                chat_id=message.message.chat.id,
                message_id=message.message.message_id,
                text=text,
                reply_markup=get_wallet_keyboard(),
                parse_mode="HTML"
            )
            data['last_wallet_msg_id'] = message.message.message_id
    else:
        sent_msg = await safe_send_message(
            chat_id=message.chat.id,
            text=text,
            reply_markup=get_wallet_keyboard(),
            parse_mode="HTML"
        )
        if sent_msg:
            data['last_wallet_msg_id'] = sent_msg.message_id

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    set_state(message.from_user.id, 'IDLE')
    await render_wallet(message, edit=False)

@dp.callback_query(F.data.startswith("action_"))
async def handle_wallet_actions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data
    data = get_user_data(user_id)

    if action == "action_close":
        try:
            await callback.message.delete()
        except:
            pass
        await callback.answer()
        return

    if action == "action_deposit":
        set_state(user_id, 'DEPOSIT')
        await safe_send_message(
            chat_id=callback.message.chat.id,
            text="💸 <b>Пополнение баланса</b>\n\nВведите сумму:",
            reply_markup=ForceReply(input_field_placeholder="Например: 1000"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    if action == "action_withdraw":
        if data['balance'] <= 0:
            await callback.answer("⚠️ На балансе недостаточно средств!", show_alert=True)
            return
        
        set_state(user_id, 'WITHDRAW')
        await safe_send_message(
            chat_id=callback.message.chat.id,
            text=f"💸 <b>Снятие средств</b>\n\nДоступно: {data['balance']:.2f} RUB\nВведите сумму:",
            reply_markup=ForceReply(input_field_placeholder="Например: 500"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

@dp.message(F.text)
async def handle_text_input(message: types.Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    state = data['state']

    if state == 'IDLE':
        return 

    try:
        clean_input = message.text.replace(',', '.').strip()
        amount = float(clean_input)
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
    except ValueError:
        await safe_send_message(chat_id=message.chat.id, text="❌ Ошибка: Введите корректное положительное число.")
        set_state(user_id, 'IDLE')
        return

    if state == 'DEPOSIT':
        update_balance(user_id, amount)
        set_state(user_id, 'IDLE')
        
        try:
            await message.delete()
        except:
            pass
            
        last_msg_id = data.get('last_wallet_msg_id')
        if last_msg_id:
            await safe_edit_message(
                chat_id=user_id,
                message_id=last_msg_id,
                text=f"💳 <b>Личный Кошелек</b>\n\nТекущий баланс: <b>{data['balance']:.2f} RUB</b>\n\nВыберите действие:",
                reply_markup=get_wallet_keyboard(),
                parse_mode="HTML"
            )
            success = await safe_send_message(chat_id=message.chat.id, text=f"✅ +{amount:.2f} RUB")
            if success:
                await asyncio.sleep(2)
                try: await success.delete()
                except: pass

    elif state == 'WITHDRAW':
        if amount > data['balance']:
            err_msg = await safe_send_message(chat_id=message.chat.id, text=f"❌ Недостаточно средств. Баланс: {data['balance']:.2f} RUB")
            await asyncio.sleep(3)
            if err_msg:
                try: await err_msg.delete()
                except: pass
            try: await message.delete()
            except: pass
            return
            
        update_balance(user_id, -amount)
        set_state(user_id, 'IDLE')
        
        try:
            await message.delete()
        except:
            pass

        last_msg_id = data.get('last_wallet_msg_id')
        if last_msg_id:
            await safe_edit_message(
                chat_id=user_id,
                message_id=last_msg_id,
                text=f"💳 <b>Личный Кошелек</b>\n\nТекущий баланс: <b>{data['balance']:.2f} RUB</b>\n\nВыберите действие:",
                reply_markup=get_wallet_keyboard(),
                parse_mode="HTML"
            )
            success = await safe_send_message(chat_id=message.chat.id, text=f"✅ -{amount:.2f} RUB")
            if success:
                await asyncio.sleep(2)
                try: await success.delete()
                except: pass

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
    print(f"Fake server started on port {PORT}")

# --- ЗАПУСК ---
async def main():
    # Запускаем фиктивный сервер для Render
    asyncio.create_task(start_fake_server())
    
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())