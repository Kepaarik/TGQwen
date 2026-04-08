import asyncio
import logging
from aiogram import Router, types, F
from aiogram.filters import Command
from aiogram.types import ChatMemberUpdated
from keyboards.inline_kb import get_main_menu, get_extra_menu
from aiogram.fsm.context import FSMContext
from services.finance_calc import get_personal_wallet_text, format_balance_tree
from services.event_checker import check_and_send_greetings
from database.events_db import save_user_chat

router = Router()
logger = logging.getLogger(__name__)

# Глобальная переменная для хранения ссылки на bot
_bot_ref = None

def set_bot_ref(bot):
    """Сохраняем ссылку на бота для использования в хендлерах"""
    global _bot_ref
    _bot_ref = bot

def get_bot_ref():
    """Получаем ссылку на бота"""
    return _bot_ref

async def ensure_clean_state(message_or_call, state: FSMContext):
    await state.clear()

@router.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await ensure_clean_state(message, state)
    
    # Сохраняем информацию о личном чате с пользователем
    try:
        await save_user_chat(
            user_id=message.from_user.id,
            chat_id=str(message.from_user.id),
            chat_type="private",
            title=message.from_user.full_name,
            username=message.from_user.username
        )
    except Exception as e:
        logger.warning(f"Не удалось сохранить информацию о чате пользователя: {e}")
    
    # "Будим" бота - проверяем события сразу при старте
    if _bot_ref is not None:
        logger.info("Команда /start получена, проверяем события...")
        try:
            await check_and_send_greetings(_bot_ref)
        except Exception as e:
            logger.error(f"Ошибка при проверке событий в /start: {e}")
    
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

@router.my_chat_member()
async def track_bot_added_to_group(event: ChatMemberUpdated):
    """Отслеживает добавление бота в группу"""
    if event.new_chat_member.status in ["member", "administrator", "creator"]:
        # Бот был добавлен в группу
        chat = event.chat
        user = event.from_user
        
        try:
            await save_user_chat(
                user_id=user.id,
                chat_id=str(chat.id),
                chat_type=chat.type,
                title=chat.title,
                username=chat.username if hasattr(chat, 'username') else None
            )
            logger.info(f"Бот добавлен в группу: {chat.title} ({chat.id}) пользователем {user.full_name}")
        except Exception as e:
            logger.warning(f"Не удалось сохранить информацию о группе: {e}")
    elif event.new_chat_member.status == "left":
        # Бот был удален из группы
        chat = event.chat
        user = event.from_user
        
        try:
            from database.events_db import remove_user_chat
            await remove_user_chat(user.id, str(chat.id))
            logger.info(f"Бот удален из группы: {chat.title} ({chat.id})")
        except Exception as e:
            logger.warning(f"Не удалось удалить информацию о группе: {e}")
