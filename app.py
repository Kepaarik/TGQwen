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
BOT_TOKEN = '8788194731:AAGKYQ6ur_aR5sh4INVRqSNNl8f_I3dXLfs'
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

# --- БЕЗОПАСНЫЕ ФУНКЦИИ ОТПРАВКИ ---

async def safe_send_message(chat_id, text, **kwargs):
    try:
        return await bot.send_message(chat_id, text, **kwargs)
    except TelegramForbiddenError:
        logging.warning(f"Bot kicked from chat {chat_id}")
    except Exception as e:
        logging.error(f"Send error: {e}")
    return None

async def safe_edit_message(chat_id, message_id, text, **kwargs):
    try:
        return await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, **kwargs)
    except TelegramForbiddenError:
        logging.warning(f"Bot kicked from chat {chat_id}")
    except Exception as e:
        logging.error(f"Edit error: {e}")
    return None

async def safe_delete_message(chat_id, message_id):
    """Безопасное удаление сообщения"""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramForbiddenError:
        pass # Бота кикнули или нет прав
    except Exception as e:
        # Игнорируем ошибку, если сообщение уже удалено пользователем
        if "message to delete not found" not in str(e).lower():
            logging.debug(f"Delete error: {e}")

# --- ОСНОВНАЯ ЛОГИКА ---

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

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # 1. Сначала отправляем меню
    set_state(message.from_user.id, 'IDLE')
    await render_wallet(message, edit=False)
    
    # 2. Затем удаляем команду пользователя (/start)
    # Делаем это в фоне или просто вызываем, не ожидая результата, чтобы не блокировать ответ
    asyncio.create_task(safe_delete_message(message.chat.id, message.message_id))

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
        req_msg = await safe_send_message(
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
        req_msg = await safe_send_message(
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

    # Пытаемся удалить сообщение пользователя с суммой сразу, чтобы было чисто
    # Но сначала проверим валидность, чтобы не удалять ошибочный ввод без ответа? 
    # Нет, лучше удалить всегда, а ответ дать новым сообщением.
    
    try:
        clean_input = message.text.replace(',', '.').strip()
        amount = float(clean_input)
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
    except ValueError:
        await safe_send_message(chat_id=message.chat.id, text="❌ Ошибка: Введите корректное положительное число.")
        set_state(user_id, 'IDLE')
        await safe_delete_message(message.chat.id, message.message_id) # Удаляем неверный ввод
        return

    # Удаляем ввод пользователя
    await safe_delete_message(message.chat.id, message.message_id)

    if state == 'DEPOSIT':
        update_balance(user_id, amount)
        set_state(user_id, 'IDLE')
            
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
                await safe_delete_message(success.chat.id, success.message_id)

    elif state == 'WITHDRAW':
        if amount > data['balance']:
            err_msg = await safe_send_message(chat_id=message.chat.id, text=f"❌ Недостаточно средств. Баланс: {data['balance']:.2f} RUB")
            await asyncio.sleep(3)
            if err_msg:
                await safe_delete_message(err_msg.chat.id, err_msg.message_id)
            return
            
        update_balance(user_id, -amount)
        set_state(user_id, 'IDLE')

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
                await safe_delete_message(success.chat.id, success.message_id)

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
    asyncio.create_task(start_fake_server())
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())