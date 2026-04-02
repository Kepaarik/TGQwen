import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    InlineKeyboardMarkup, InlineKeyboardButton,
    WebAppInfo, ForceReply
)
from aiogram.utils.keyboard import InlineKeyboardBuilder
# ЗАМЕНИТЕ НА ВАШ ТОКЕН
BOT_TOKEN = '8788194731:AAGKYQ6ur_aR5sh4INVRqSNNl8f_I3dXLfs'
# ЗАМЕНИТЕ НА URL ВАШЕГО WEB APP (должен быть HTTPS)
WEB_APP_URL = 'https://chat.qwen.ai/s/deploy/t_bcde28a9-8987-41a1-86e4-eeed2f418ab3' 
logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# --- ХРАНИЛИЩЕ СОСТОЯНИЙ (В реальном проекте используйте Redis/DB) ---
# Структура: { user_id: { 'current_menu': 'main', 'counter': 0 } }
user_states = {}

def get_user_state(user_id: int):
    if user_id not in user_states:
        user_states[user_id] = {'current_menu': 'main', 'counter': 0, 'username': 'User'}
    return user_states[user_id]

def set_user_state(user_id: int, key: str, value):
    if user_id not in user_states:
        user_states[user_id] = {'current_menu': 'main', 'counter': 0, 'username': 'User'}
    user_states[user_id][key] = value

# --- ГЕНЕРАТОРЫ КЛАВИАТУР ---

def get_main_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="📊 Статистика", callback_data="menu_stats"))
    builder.row(InlineKeyboardButton(text="⚙️ Настройки", callback_data="menu_settings"))
    builder.row(InlineKeyboardButton(text="🌐 Web App Demo", web_app=WebAppInfo(url=WEB_APP_URL)))
    builder.row(InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu"))
    return builder.as_markup()

def get_stats_kb(current_count: int):
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=f"👁 Просмотров: {current_count}", callback_data="noop")) # Неактивная кнопка
    builder.row(
        InlineKeyboardButton(text="➕ Добавить", callback_data="action_add"),
        InlineKeyboardButton(text="➖ Убрать", callback_data="action_remove")
    )
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back"))
    return builder.as_markup()

def get_settings_kb():
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔔 Уведомления: ВКЛ", callback_data="toggle_notify_on"))
    builder.row(InlineKeyboardButton(text="📝 Изменить имя", callback_data="action_change_name"))
    builder.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back"))
    return builder.as_markup()

# --- ОБРАБОТЧИКИ ---

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    set_user_state(user_id, 'username', message.from_user.full_name)
    
    text = (
        f"👋 Привет, {message.from_user.full_name}!\n"
        f"Это демо-интерфейс в стиле TGgemini.\n"
        f"Используйте кнопки ниже для навигации."
    )
    await message.answer(text, reply_markup=get_main_kb())

# --- ГЛАВНЫЙ ОБРАБОТЧИК INLINE КНОПОК ---
@dp.callback_query(F.data.startswith("menu_") | F.data.startswith("action_") | F.data.startswith("toggle_") | F.data == "close_menu" | F.data == "noop")
async def process_inline_navigation(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data
    state = get_user_state(user_id)
    
    # 1. Закрытие меню
    if data == "close_menu":
        await callback.message.delete()
        await callback.answer()
        return

    # 2. Навигация: Главное меню
    if data == "menu_back":
        set_user_state(user_id, 'current_menu', 'main')
        text = "🏠 Главное меню"
        kb = get_main_kb()
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
        return

    # 3. Навигация: Статистика
    if data == "menu_stats":
        set_user_state(user_id, 'current_menu', 'stats')
        count = state['counter']
        text = f"📊 Ваша статистика\n\nТекущее значение счетчика: <b>{count}</b>"
        kb = get_stats_kb(count)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()
        return

    # 4. Навигация: Настройки
    if data == "menu_settings":
        set_user_state(user_id, 'current_menu', 'settings')
        text = "⚙️ Настройки профиля"
        kb = get_settings_kb()
        await callback.message.edit_text(text, reply_markup=kb)
        await callback.answer()
        return

    # 5. Действие: Изменение счетчика
    if data == "action_add":
        state['counter'] += 1
        set_user_state(user_id, 'counter', state['counter'])
        # Обновляем сообщение с новым значением
        text = f"📊 Ваша статистика\n\nТекущее значение счетчика: <b>{state['counter']}</b>"
        kb = get_stats_kb(state['counter'])
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer("Значение увеличено!")
        return

    if data == "action_remove":
        if state['counter'] > 0:
            state['counter'] -= 1
            set_user_state(user_id, 'counter', state['counter'])
            text = f"📊 Ваша статистика\n\nТекущее значение счетчика: <b>{state['counter']}</b>"
            kb = get_stats_kb(state['counter'])
            await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            await callback.answer("Значение уменьшено!")
        else:
            await callback.answer("Нельзя уменьшить ниже 0!", show_alert=True)
        return

    # 6. Действие: Переключатель уведомлений
    if data.startswith("toggle_notify"):
        is_on = "on" in data
        new_status = "off" if is_on else "on"
        new_text_btn = "🔔 Уведомления: ВЫКЛ" if is_on else "🔔 Уведомления: ВКЛ"
        
        # Меняем кнопку в клавиатуре
        kb = InlineKeyboardBuilder()
        kb.row(InlineKeyboardButton(text=new_text_btn, callback_data=f"toggle_notify_{new_status}"))
        kb.row(InlineKeyboardButton(text="📝 Изменить имя", callback_data="action_change_name"))
        kb.row(InlineKeyboardButton(text="🔙 Назад", callback_data="menu_back"))
        
        await callback.message.edit_reply_markup(reply_markup=kb.as_markup())
        await callback.answer(f"Уведомления переключены: {new_status.upper()}")
        return

    # 7. Действие: Изменение имени (Эмуляция ввода)
    if data == "action_change_name":
        await callback.message.edit_text(
            "✍️ Введите новое имя в поле ниже:",
            reply_markup=ForceReply(input_field_placeholder="Ваше новое имя")
        )
        await callback.answer()
        return

    # Пустышка для неактивных кнопок
    if data == "noop":
        await callback.answer()

# --- ОБРАБОТКА ВВОДА ИМЕНИ (Force Reply) ---
@dp.message(F.reply_to_message is not None)
async def handle_name_change(message: types.Message):
    # Проверяем, что это ответ на наше сообщение с запросом имени
    # В реальном боте лучше проверять ID сообщения из базы данных
    if "Введите новое имя" in message.reply_to_message.text:
        new_name = message.text
        user_id = message.from_user.id
        set_user_state(user_id, 'username', new_name)
        
        # Возвращаем меню настроек
        kb = get_settings_kb()
        await message.answer(
            f"✅ Имя изменено на: <b>{new_name}</b>",
            reply_markup=kb,
            parse_mode="HTML"
        )

# --- ЗАПУСК ---
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен в режиме Polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())