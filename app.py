import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ForceReply
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГУРАЦИЯ ---
BOT_TOKEN = 'ВАШ_ТОКЕН'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ИМИТАЦИЯ БАЗЫ ДАННЫХ (В памяти) ---
# Структура: { user_id: balance }
user_balances = {}

def get_balance(user_id: int) -> float:
    return user_balances.get(user_id, 0.0)

def update_balance(user_id: int, amount: float):
    if user_id not in user_balances:
        user_balances[user_id] = 0.0
    user_balances[user_id] += amount

# --- СЛОВАРЬ СОСТОЯНИЙ ПОЛЬЗОВАТЕЛЯ ---
# Нужно знать, какое действие ожидает ввода от пользователя
# States: 'idle', 'waiting_for_deposit', 'waiting_for_withdraw'
user_actions = {}

def set_action(user_id: int, action: str):
    user_actions[user_id] = action

def get_action(user_id: int) -> str:
    return user_actions.get(user_id, 'idle')

def clear_action(user_id: int):
    if user_id in user_actions:
        del user_actions[user_id]

# --- ГЕНЕРАТОРЫ ИНТЕРФЕЙСА ---

def create_wallet_kb():
    """Клавиатура кошелька"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Пополнить", callback_data="wallet_deposit"),
        InlineKeyboardButton(text="➖ Снять", callback_data="wallet_withdraw")
    )
    builder.row(InlineKeyboardButton(text="🔄 История (Демо)", callback_data="wallet_history"))
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu"))
    return builder.as_markup()

def get_wallet_text(user_id: int):
    balance = get_balance(user_id)
    return (
        f"💳 <b>Мой Кошелек</b>\n\n"
        f"Текущий баланс: <b>{balance:.2f} ₽</b>\n\n"
        f"Выберите действие:"
    )

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Инициализируем баланс если нет
    if message.from_user.id not in user_balances:
        user_balances[message.from_user.id] = 0.0
    
    await show_wallet(message.chat.id, message.from_user.id)

async def show_wallet(chat_id: int, user_id: int, message_id: int = None):
    """Отправляет новое сообщение или редактирует существующее"""
    text = get_wallet_text(user_id)
    kb = create_wallet_kb()
    
    if message_id:
        try:
            await bot.edit_message_text(
                chat_id=chat_id,
                message_id=message_id,
                text=text,
                reply_markup=kb,
                parse_mode="HTML"
            )
        except Exception as e:
            logging.warning(f"Ошибка редактирования: {e}")
    else:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            reply_markup=kb,
            parse_mode="HTML"
        )

# --- ОБРАБОТКА INLINE КНОПОК КОШЕЛЬКА ---

@dp.callback_query(F.data.startswith("wallet_") | F.data == "close_menu")
async def process_wallet_actions(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    message_id = callback.message.message_id
    chat_id = callback.message.chat.id

    # 1. Закрытие
    if data == "close_menu":
        await callback.message.delete()
        await callback.answer()
        return

    # 2. История (просто заглушка)
    if data == "wallet_history":
        await callback.answer("История пуста (демо-режим)", show_alert=True)
        return

    # 3. Пополнение
    if data == "wallet_deposit":
        set_action(user_id, 'waiting_for_deposit')
        await callback.message.edit_text(
            text="💸 <b>Пополнение баланса</b>\n\nВведите сумму пополнения (число):",
            reply_markup=ForceReply(input_field_placeholder="Например: 1000"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

    # 4. Снятие
    if data == "wallet_withdraw":
        balance = get_balance(user_id)
        if balance <= 0:
            await callback.answer("Недостаточно средств для снятия!", show_alert=True)
            return
        
        set_action(user_id, 'waiting_for_withdraw')
        await callback.message.edit_text(
            text=f"💸 <b>Снятие средств</b>\n\nДоступно: {balance:.2f} ₽\nВведите сумму для снятия:",
            reply_markup=ForceReply(input_field_placeholder="Например: 500"),
            parse_mode="HTML"
        )
        await callback.answer()
        return

# --- ОБРАБОТКА ВВОДА СУММЫ (TEXT) ---

@dp.message(F.text)
async def handle_amount_input(message: types.Message):
    user_id = message.from_user.id
    action = get_action(user_id)
    
    # Если пользователь не в режиме ввода денег, игнорируем или предлагаем начать
    if action == 'idle':
        # Можно добавить реакцию на обычные сообщения, если нужно
        return

    # Пытаемся распарсить число
    try:
        amount = float(message.text.replace(',', '.')) # Замена запятой на точку
        if amount <= 0:
            raise ValueError("Сумма должна быть положительной")
    except ValueError:
        await message.answer("❌ Ошибка: Введите корректное положительное число.")
        # Возвращаем меню, но сбрасываем действие, чтобы пользователь начал заново через кнопку
        clear_action(user_id)
        await show_wallet(message.chat.id, user_id)
        return

    # Логика действий
    if action == 'waiting_for_deposit':
        update_balance(user_id, amount)
        clear_action(user_id)
        
        # Отправляем подтверждение и возвращаем меню
        sent_msg = await message.answer(f"✅ Успешно! Баланс пополнен на {amount:.2f} ₽")
        # Небольшая задержка для красоты, затем показываем кошелек
        await asyncio.sleep(1.5)
        await sent_msg.delete() # Удаляем подтверждение, чтобы не засорять чат
        await show_wallet(message.chat.id, user_id)

    elif action == 'waiting_for_withdraw':
        current_balance = get_balance(user_id)
        if amount > current_balance:
            await message.answer(f"❌ Ошибка: Недостаточно средств. Ваш баланс: {current_balance:.2f} ₽")
            # Не сбрасываем действие, даем попробовать снова
            return
        
        update_balance(user_id, -amount)
        clear_action(user_id)
        
        sent_msg = await message.answer(f"✅ Успешно! Списано {amount:.2f} ₽")
        await asyncio.sleep(1.5)
        await sent_msg.delete()
        await show_wallet(message.chat.id, user_id)

# --- ЗАПУСК ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен. Используйте /start")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())