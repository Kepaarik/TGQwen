import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = '8788194731:AAGKYQ6ur_aR5sh4INVRqSNNl8f_I3dXLfs'  # <-- ВСТАВЬТЕ СЮДА ВАШ ТОКЕН

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ХРАНИЛИЩЕ ДАННЫХ (ОПЕРАТИВНАЯ ПАМЯТЬ) ---
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

# --- ФУНКЦИИ ОТОБРАЖЕНИЯ ---

async def render_wallet(message: types.Message | types.CallbackQuery, edit: bool = True):
    """Отрисовывает текущее состояние кошелька"""
    user_id = message.from_user.id
    data = get_user_data(user_id)
    
    text = (
        f"💳 <b>Личный Кошелек</b>\n\n"
        f"Текущий баланс: <b>{data['balance']:.2f} RUB</b>\n\n"
        f"Выберите действие:"
    )
    
    # Если это CallbackQuery (нажатие кнопки), редактируем сообщение
    if isinstance(message, types.CallbackQuery):
        if edit:
            try:
                await message.message.edit_text(text, reply_markup=get_wallet_keyboard(), parse_mode="HTML")
                # Сохраняем ID сообщения, чтобы потом его обновлять
                data['last_wallet_msg_id'] = message.message.message_id
            except Exception as e:
                logging.error(f"Ошибка редактирования: {e}")
    else:
        # Если это обычное сообщение (команда /start), отправляем новое
        sent_msg = await message.answer(text, reply_markup=get_wallet_keyboard(), parse_mode="HTML")
        data['last_wallet_msg_id'] = sent_msg.message_id

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    set_state(message.from_user.id, 'IDLE')
    await render_wallet(message, edit=False)

# --- ОБРАБОТЧИКИ INLINE КНОПОК ---

@dp.callback_query(F.data.startswith("action_"))
async def handle_wallet_actions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    action = callback.data
    data = get_user_data(user_id)

    # 1. ЗАКРЫТЬ МЕНЮ
    if action == "action_close":
        try:
            await callback.message.delete()
        except:
            pass
        await callback.answer()
        return

    # 2. ПОПОЛНЕНИЕ
    if action == "action_deposit":
        set_state(user_id, 'DEPOSIT')
        # ОШИБКА БЫЛА ЗДЕСЬ: Нельзя использовать ForceReply в edit_text.
        # Мы отправляем НОВОЕ сообщение с запросом ввода.
        await callback.message.answer(
            text="💸 <b>Пополнение баланса</b>\n\nВведите сумму:",
            reply_markup=ForceReply(input_field_placeholder="Например: 1000"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # 3. СНЯТИЕ
    if action == "action_withdraw":
        if data['balance'] <= 0:
            await callback.answer("⚠️ На балансе недостаточно средств!", show_alert=True)
            return
        
        set_state(user_id, 'WITHDRAW')
        # Также отправляем новое сообщение
        await callback.message.answer(
            text=f"💸 <b>Снятие средств</b>\n\nДоступно: {data['balance']:.2f} RUB\nВведите сумму:",
            reply_markup=ForceReply(input_field_placeholder="Например: 500"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

# --- ОБРАБОТЧИК ТЕКСТОВЫХ ВВОДОВ (СУММ) ---

@dp.message(F.text)
async def handle_text_input(message: types.Message):
    user_id = message.from_user.id
    data = get_user_data(user_id)
    state = data['state']

    # Если пользователь не в режиме ввода, игнорируем
    if state == 'IDLE':
        return 

    # Пытаемся преобразовать ввод в число
    try:
        clean_input = message.text.replace(',', '.').strip()
        amount = float(clean_input)
        
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
            
    except ValueError:
        await message.answer("❌ Ошибка: Введите корректное положительное число.")
        # Сбрасываем состояние и возвращаем меню
        set_state(user_id, 'IDLE')
        # Так как у нас нет ссылки на старое сообщение в этом хендлере напрямую,
        # просто сбрасываем состояние. Пользователь может нажать /start или кнопки снова.
        return

    # ЛОГИКА ПОПОЛНЕНИЯ
    if state == 'DEPOSIT':
        update_balance(user_id, amount)
        set_state(user_id, 'IDLE')
        
        # Удаляем сообщение пользователя с суммой, чтобы не засорять чат
        try:
            await message.delete()
        except:
            pass
            
        # Находим последнее сообщение с кошельком и обновляем его
        last_msg_id = data.get('last_wallet_msg_id')
        if last_msg_id:
            try:
                # Используем bot.edit_message_text напрямую, так как у нас есть ID
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=last_msg_id,
                    text=f"💳 <b>Личный Кошелек</b>\n\nТекущий баланс: <b>{data['balance']:.2f} RUB</b>\n\nВыберите действие:",
                    reply_markup=get_wallet_keyboard(),
                    parse_mode="HTML"
                )
                # Отправляем краткое уведомление об успехе
                success = await message.answer(f"✅ +{amount:.2f} RUB")
                await asyncio.sleep(2)
                await success.delete()
            except Exception as e:
                logging.error(f"Не удалось обновить меню: {e}")
                # Фолбэк: если не вышло отредактировать, просто пишем успех
                await message.answer(f"✅ Баланс пополнен. Новый баланс: {data['balance']:.2f} RUB")

    # ЛОГИКА СНЯТИЯ
    elif state == 'WITHDRAW':
        if amount > data['balance']:
            err_msg = await message.answer(f"❌ Недостаточно средств. Баланс: {data['balance']:.2f} RUB")
            await asyncio.sleep(3)
            await err_msg.delete()
            await message.delete() # Удаляем неверный ввод
            return
            
        update_balance(user_id, -amount)
        set_state(user_id, 'IDLE')
        
        try:
            await message.delete()
        except:
            pass

        last_msg_id = data.get('last_wallet_msg_id')
        if last_msg_id:
            try:
                await bot.edit_message_text(
                    chat_id=user_id,
                    message_id=last_msg_id,
                    text=f"💳 <b>Личный Кошелек</b>\n\nТекущий баланс: <b>{data['balance']:.2f} RUB</b>\n\nВыберите действие:",
                    reply_markup=get_wallet_keyboard(),
                    parse_mode="HTML"
                )
                success = await message.answer(f"✅ -{amount:.2f} RUB")
                await asyncio.sleep(2)
                await success.delete()
            except Exception as e:
                logging.error(f"Не удалось обновить меню: {e}")
                await message.answer(f"✅ Средства сняты. Новый баланс: {data['balance']:.2f} RUB")

# --- ЗАПУСК ---
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())