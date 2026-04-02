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
# Структура: { user_id: { 'balance': float, 'state': str } }
# state может быть: 'IDLE', 'DEPOSIT', 'WITHDRAW'
users_db = {}

def get_user_data(user_id: int):
    if user_id not in users_db:
        users_db[user_id] = {'balance': 0.0, 'state': 'IDLE'}
    return users_db[user_id]

def update_balance(user_id: int, amount: float):
    data = get_user_data(user_id)
    data['balance'] += amount

def set_state(user_id: int, state: str):
    data = get_user_data(user_id)
    data['state'] = state

# --- КЛАВИАТУРЫ ---

def get_wallet_keyboard():
    """Основная клавиатура кошелька"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="➕ Пополнить баланс", callback_data="action_deposit"),
        InlineKeyboardButton(text="➖ Снять средства", callback_data="action_withdraw")
    )
    builder.row(InlineKeyboardButton(text="❌ Закрыть меню", callback_data="action_close"))
    return builder.as_markup()

# --- ФУНКЦИИ ОТОБРАЖЕНИЯ ---

async def render_wallet(message: types.Message | types.CallbackQuery, edit: bool = False):
    """Отрисовывает текущее состояние кошелька"""
    user_id = message.from_user.id
    data = get_user_data(user_id)
    
    text = (
        f"💳 <b>Личный Кошелек</b>\n\n"
        f"Текущий баланс: <b>{data['balance']:.2f} RUB</b>\n\n"
        f"Выберите действие:"
    )
    
    if isinstance(message, types.CallbackQuery):
        if edit:
            try:
                await message.message.edit_text(text, reply_markup=get_wallet_keyboard(), parse_mode="HTML")
            except Exception as e:
                print(f"Ошибка редактирования: {e}")
        else:
            # Если это новый вызов без edit (редкий кейс для этого бота)
            await message.message.answer(text, reply_markup=get_wallet_keyboard(), parse_mode="HTML")
    else:
        # Это обычное сообщение (например, после старта)
        await message.answer(text, reply_markup=get_wallet_keyboard(), parse_mode="HTML")

# --- ОБРАБОТЧИКИ КОМАНД ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    # Сброс состояния при старте
    set_state(message.from_user.id, 'IDLE')
    await render_wallet(message)

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
        await callback.message.edit_text(
            text="💸 <b>Пополнение баланса</b>\n\nВведите сумму, на которую хотите пополнить счет:",
            reply_markup=ForceReply(input_field_placeholder="Введите сумму (например: 100)"),
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
        await callback.message.edit_text(
            text=f"💸 <b>Снятие средств</b>\n\nДоступно: {data['balance']:.2f} RUB\nВведите сумму для снятия:",
            reply_markup=ForceReply(input_field_placeholder="Введите сумму"),
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

    # Если пользователь не в режиме ввода денег, игнорируем текст 
    # (или можно добавить обработку других команд здесь)
    if state == 'IDLE':
        # Если пользователь пишет текст, когда ничего не выбрано, 
        # можно предложить нажать /start
        return 

    # Пытаемся преобразовать ввод в число
    try:
        # Заменяем запятую на точку для удобства (100,5 -> 100.5)
        clean_input = message.text.replace(',', '.').strip()
        amount = float(clean_input)
        
        if amount <= 0:
            raise ValueError("Сумма должна быть больше нуля")
            
    except ValueError:
        await message.answer("❌ Ошибка: Пожалуйста, введите корректное положительное число.")
        # Возвращаем пользователя в меню, сбрасывая состояние
        set_state(user_id, 'IDLE')
        await render_wallet(message)
        return

    # ЛОГИКА ПОПОЛНЕНИЯ
    if state == 'DEPOSIT':
        update_balance(user_id, amount)
        set_state(user_id, 'IDLE') # Сбрасываем состояние
        
        # Отправляем временное уведомление об успехе
        success_msg = await message.answer(f"✅ Баланс успешно пополнен на <b>{amount:.2f} RUB</b>", parse_mode="HTML")
        
        # Через 2 секунды удаляем уведомление и показываем обновленный кошелек
        await asyncio.sleep(2)
        try:
            await success_msg.delete()
            await message.delete() # Удаляем также ввод пользователя для чистоты
        except:
            pass
        await render_wallet(message)

    # ЛОГИКА СНЯТИЯ
    elif state == 'WITHDRAW':
        if amount > data['balance']:
            await message.answer(f"❌ Ошибка: Недостаточно средств. Ваш баланс: {data['balance']:.2f} RUB")
            # Не сбрасываем состояние, даем попробовать ввести меньшую сумму
            return
            
        update_balance(user_id, -amount)
        set_state(user_id, 'IDLE') # Сбрасываем состояние
        
        success_msg = await message.answer(f"✅ Средства успешно сняты: <b>{amount:.2f} RUB</b>", parse_mode="HTML")
        
        await asyncio.sleep(2)
        try:
            await success_msg.delete()
            await message.delete()
        except:
            pass
        await render_wallet(message)

# --- ЗАПУСК ---
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())