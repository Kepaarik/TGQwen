import asyncio
import logging
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton,
    Message
)

# Включите логирование
logging.basicConfig(level=logging.INFO)

# ЗАМЕНИТЕ НА ВАШ ТОКЕН
BOT_TOKEN = '8788194731:AAGKYQ6ur_aR5sh4INVRqSNNl8f_I3dXLfs'
# ЗАМЕНИТЕ НА URL ВАШЕГО WEB APP (должен быть HTTPS)
WEB_APP_URL = 'https://chat.qwen.ai/s/deploy/t_bcde28a9-8987-41a1-86e4-eeed2f418ab3' 

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# -------------------------------------------------------------------
# Хелпер для определения контекста (ЛС или Группа)
# -------------------------------------------------------------------
def get_context_info(message: Message):
    user = message.from_user
    chat = message.chat
    
    context = {
        "user_id": user.id,
        "user_name": user.full_name,
        "chat_id": chat.id,
        "chat_type": chat.type, # 'private', 'group', 'supergroup', 'channel'
        "is_group": chat.type in ['group', 'supergroup']
    }
    return context

# -------------------------------------------------------------------
# 1. Команда /start
# -------------------------------------------------------------------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    ctx = get_context_info(message)
    
    text = (
        f"Привет, {ctx['user_name']}!\n"
        f"Мы находимся в чате типа: <b>{ctx['chat_type']}</b>.\n"
        f"ID чата: <code>{ctx['chat_id']}</code>\n\n"
        f"Выберите способ взаимодействия:"
    )

    # Создаем Reply Keyboard с Web App
    # WebAppInfo требует точный URL
    kb = ReplyKeyboardMarkup(keyboard=[
        [
            KeyboardButton(text="🌐 Открыть Web App (Reply)", web_app=WebAppInfo(url=WEB_APP_URL))
        ],
        [
            KeyboardButton(text="📝 Обычный текст"),
            KeyboardButton(text="📍 Геолокация")
        ]
    ], resize_keyboard=True, input_field_placeholder="Нажмите кнопку ниже...")

    await message.answer(text, reply_markup=kb, parse_mode="HTML")

# -------------------------------------------------------------------
# 2. Обработка данных от Web App (когда юзер жмет "Отправить" внутри HTML)
# -------------------------------------------------------------------
@dp.message(F.web_app_data)
async def handle_web_app_data(message: types.Message):
    ctx = get_context_info(message)
    
    # Данные приходят в виде строки JSON
    data_str = message.web_app_data.data
    try:
        data = json.loads(data_str)
        response_text = (
            f"✅ Получены данные из Web App!\n"
            f"Пользователь: {ctx['user_name']} (ID: {ctx['user_id']})\n"
            f"Чат: {ctx['chat_type']} (ID: {ctx['chat_id']})\n"
            f"Данные: <code>{data_str}</code>"
        )
    except json.JSONDecodeError:
        response_text = f"Получены сырые данные: {data_str}"

    # Отвечаем в тот же чат, откуда пришел запрос
    await message.answer(response_text, parse_mode="HTML")

# -------------------------------------------------------------------
# 3. Демонстрация Inline Web App (работает в группах лучше)
# -------------------------------------------------------------------
@dp.message(Command("inline_wa"))
async def cmd_inline_wa(message: types.Message):
    ctx = get_context_info(message)
    
    # Inline клавиатура с кнопкой Web App
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Запустить Mini App (Inline)", web_app=WebAppInfo(url=WEB_APP_URL))]
    ])
    
    await message.answer(
        f"Нажмите кнопку ниже, чтобы открыть Web App.\n"
        f"Это работает даже в группах, если бот имеет право отправлять сообщения.",
        reply_markup=inline_kb
    )

# -------------------------------------------------------------------
# 4. Обработка обычных сообщений (для проверки контекста в группах)
# -------------------------------------------------------------------
@dp.message(F.text == "📝 Обычный текст")
async def handle_text_btn(message: types.Message):
    ctx = get_context_info(message)
    prefix = "📢 В группе" if ctx['is_group'] else "👤 В ЛС"
    await message.answer(f"{prefix}: Вы нажали кнопку текста. Ваш ID: {ctx['user_id']}")

@dp.message(F.text == "📍 Геолокация")
async def handle_loc_btn(message: types.Message):
    # Кнопка запроса геолокации работает только в Reply Keyboard
    kb = ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text="Отправить мою геопозицию", request_location=True)]
    ], resize_keyboard=True)
    await message.answer("Нажмите кнопку ниже:", reply_markup=kb)

@dp.message(F.location)
async def handle_location(message: types.Message):
    ctx = get_context_info(message)
    await message.answer(
        f"📍 Получена локация от {ctx['user_name']} в чате {ctx['chat_type']}.\n"
        f"Sh: {message.location.latitude}, Ln: {message.location.longitude}"
    )

# -------------------------------------------------------------------
# 5. Обработка команд в группах (чтобы бот реагировал на упоминания)
# -------------------------------------------------------------------
@dp.message(Command("test_group"))
async def cmd_test_group(message: types.Message):
    ctx = get_context_info(message)
    await message.answer(
        f"Бот активен в группе!\n"
        f"Запрос от: {ctx['user_name']}\n"
        f"Chat ID: {ctx['chat_id']}"
    )

# -------------------------------------------------------------------
# Запуск
# -------------------------------------------------------------------
async def main():
    # Удаляем вебхук, если использовался ранее
    await bot.delete_webhook(drop_pending_updates=True)
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())