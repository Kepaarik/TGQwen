from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardButton
from aiogram.exceptions import TelegramBadRequest
from keyboards.inline_kb import get_cancel_keyboard
from database.events_db import (
    get_all_events, get_event_by_id, update_event, set_greeting_time,
    get_event_chats, set_event_chats, get_user_chats, get_chat_display_info,
    chats_col
)
from config import ADMIN_ID
import logging
import asyncio
from aiogram.fsm.state import State, StatesGroup

logger = logging.getLogger(__name__)

router = Router()

# Админский ID - жестко задан
ADMIN_USER_ID = 38322917


def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id == ADMIN_USER_ID or (ADMIN_ID != 0 and user_id == ADMIN_ID)


async def check_admin_access(message_or_callback):
    """Проверка доступа администратора"""
    user_id = message_or_callback.from_user.id
    if not is_admin(user_id):
        return False
    return True


class AdminStates(StatesGroup):
    wait_new_time = State()
    wait_message_text = State()
    wait_group_binding_name = State()
    wait_group_binding_id = State()


@router.message(Command("admin"))
async def cmd_admin(message: types.Message):
    """Главное меню админ панели"""
    if not await check_admin_access(message):
        logger.warning(f"Пользователь {message.from_user.id} попытался получить доступ к админ панели")
        return

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="⏰ Настройка времени событий", callback_data="admin_event_time"))
    builder.row(InlineKeyboardButton(text="💬 Управление чатами для рассылок", callback_data="admin_broadcast_chats"))
    builder.row(InlineKeyboardButton(text="📋 Привязка ID групп к именам", callback_data="admin_group_bindings"))
    builder.row(InlineKeyboardButton(text="📨 Отправить сообщение", callback_data="admin_send_message"))
    builder.row(InlineKeyboardButton(text="✕ Закрыть", callback_data="menu_close"))

    await message.answer(
        "<b>🛡️ Админ панель</b>\n\nВыберите действие:",
        reply_markup=builder.as_markup(),
        parse_mode="HTML"
    )


# ==================== НАСТРОЙКА ВРЕМЕНИ СОБЫТИЙ ====================

@router.callback_query(F.data == "admin_event_time")
async def admin_event_time_menu(callback: types.CallbackQuery):
    """Меню настройки времени событий"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    events = await get_all_events()

    text = "<b>⏰ Настройка времени событий</b>\n\n"
    if not events:
        text += "Список событий пуст."
    else:
        for event in events[:10]:
            current_time = event.get('greeting_time', '09:00')
            text += f"• {event['description'][:30]} - {current_time}\n"

    builder = InlineKeyboardBuilder()
    for event in events[:10]:
        builder.row(InlineKeyboardButton(
            text=f"⏰ {event['description'][:25]}",
            callback_data=f"admin_edit_time_{str(event['_id'])}"
        ))

    builder.row(InlineKeyboardButton(text="← Назад", callback_data="admin"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            await callback.answer()
        else:
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("admin_edit_time_"))
async def admin_edit_event_time(callback: types.CallbackQuery, state: FSMContext):
    """Редактирование времени конкретного события"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    event_id = callback.data.replace("admin_edit_time_", "")
    event = await get_event_by_id(event_id)

    if not event:
        await callback.answer("Событие не найдено", show_alert=True)
        return

    current_time = event.get('greeting_time', '09:00')

    await state.update_data(event_id=event_id, old_message_id=callback.message.message_id)
    await state.set_state(AdminStates.wait_new_time)

    text = (
        f"<b>Редактирование времени события:</b>\n\n"
        f"Событие: {event['description']}\n"
        f"Текущее время: {current_time}\n\n"
        f"Введите новое время в формате ЧЧ:ММ (например, 08:30 или 14:00):"
    )

    try:
        msg = await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_keyboard("admin_event_time"))
        await state.update_data(old_message_id=msg.message_id)
    except Exception:
        msg = await callback.message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard("admin_event_time"))
        await state.update_data(old_message_id=msg.message_id)

    await callback.answer()


@router.message(AdminStates.wait_new_time, F.text)
async def process_admin_new_time(message: types.Message, state: FSMContext):
    """Обработка нового времени от админа"""
    time_str = message.text.strip()

    if ":" not in time_str:
        await message.answer("Ошибка: неправильный формат. Введите ЧЧ:ММ:")
        return

    try:
        parts = time_str.split(':')
        hour = int(parts[0])
        minute = int(parts[1])
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError("Неверное время")
    except:
        await message.answer("Ошибка: неверное время. Часы должны быть 0-23, минуты 0-59:")
        return

    data = await state.get_data()
    event_id = data['event_id']

    try:
        await message.delete()
    except Exception:
        pass

    await set_greeting_time(event_id, time_str)

    text = f"<b>✅ Время обновлено!</b>\n\nНовое время: {time_str}"
    await message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard("admin_event_time"))
    await state.clear()


# ==================== УПРАВЛЕНИЕ ЧАТАМИ ДЛЯ РАССЫЛОК ====================

@router.callback_query(F.data == "admin_broadcast_chats")
async def admin_broadcast_chats_menu(callback: types.CallbackQuery):
    """Меню управления чатами для рассылок"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    # Получаем все чаты из БД
    all_chats = await chats_col.find().to_list(length=100)

    text = "<b>💬 Управление чатами для рассылок</b>\n\n"
    if not all_chats:
        text += "Нет сохраненных чатов."
    else:
        text += f"Всего чатов: {len(all_chats)}\n\n"
        for chat in all_chats[:20]:
            chat_type = chat.get('chat_type', 'unknown')
            title = chat.get('title', 'Без названия')
            chat_id = chat.get('chat_id', 'N/A')
            icon = "👤" if chat_type == "private" else "👥"
            text += f"{icon} {title} (<code>{chat_id}</code>)\n"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="← Назад", callback_data="admin"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

    await callback.answer()


# ==================== ПРИВЯЗКА ID ГРУПП К ИМЕНАМ ====================

@router.callback_query(F.data == "admin_group_bindings")
async def admin_group_bindings_menu(callback: types.CallbackQuery):
    """Меню привязки ID групп к именам"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    # Получаем все группы из БД
    groups = await chats_col.find({"chat_type": {"$in": ["group", "supergroup"]}}).to_list(length=100)

    text = "<b>📋 Привязка ID групп к именам</b>\n\n"
    if not groups:
        text += "Нет сохраненных групп.\n\n"
        text += "Группы автоматически сохраняются при добавлении бота в группу."
    else:
        text += f"Всего групп: {len(groups)}\n\n"
        for group in groups[:20]:
            title = group.get('title', 'Без названия')
            chat_id = group.get('chat_id', 'N/A')
            username = group.get('username', '')
            text += f"👥 <b>{title}</b>\n"
            text += f"   ID: <code>{chat_id}</code>"
            if username:
                text += f" | @{username}"
            text += "\n\n"

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="➕ Добавить привязку", callback_data="admin_add_binding"))
    builder.row(InlineKeyboardButton(text="← Назад", callback_data="admin"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    except Exception:
        await callback.message.answer(text, reply_markup=builder.as_markup(), parse_mode="HTML")

    await callback.answer()


@router.callback_query(F.data == "admin_add_binding")
async def admin_start_add_binding(callback: types.CallbackQuery, state: FSMContext):
    """Начало добавления привязки группы"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    await state.set_state(AdminStates.wait_group_binding_id)

    text = (
        "<b>➕ Добавление привязки группы</b>\n\n"
        "Введите ID группы (например, -1001234567890):\n\n"
        "ID можно узнать, переслав сообщение из группы боту."
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_keyboard("admin_group_bindings"))
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    await callback.answer()


@router.message(AdminStates.wait_group_binding_id, F.text)
async def process_group_binding_id(message: types.Message, state: FSMContext):
    """Обработка ID группы для привязки"""
    chat_id = message.text.strip()

    # Проверяем, что это похоже на ID
    if not chat_id.lstrip('-').isdigit():
        await message.answer("Ошибка: ID должен быть числом (может начинаться с -). Введите корректный ID:")
        return

    await state.update_data(group_chat_id=chat_id)
    await state.set_state(AdminStates.wait_group_binding_name)

    await message.answer(
        f"ID сохранен: <code>{chat_id}</code>\n\n"
        f"Теперь введите название группы:",
        parse_mode="HTML",
        reply_markup=get_cancel_keyboard("admin_group_bindings")
    )
    await state.update_data(old_message_id=message.message_id)


@router.message(AdminStates.wait_group_binding_name, F.text)
async def process_group_binding_name(message: types.Message, state: FSMContext):
    """Обработка названия группы для привязки"""
    group_name = message.text.strip()
    data = await state.get_data()
    chat_id = data.get('group_chat_id')

    if not chat_id:
        await message.answer("Ошибка: ID группы не найден. Начните сначала.")
        await state.clear()
        return

    # Сохраняем привязку в БД
    try:
        await chats_col.update_one(
            {"chat_id": chat_id},
            {
                "$set": {
                    "title": group_name,
                    "chat_type": "supergroup",
                    "updated_at": __import__('datetime').datetime.now(__import__('config').MOSCOW_TZ)
                }
            },
            upsert=True
        )

        text = f"<b>✅ Привязка сохранена!</b>\n\n"
        text += f"Группа: {group_name}\n"
        text += f"ID: <code>{chat_id}</code>"

        await message.answer(text, parse_mode="HTML", reply_markup=get_cancel_keyboard("admin_group_bindings"))
    except Exception as e:
        logger.error(f"Ошибка при сохранении привязки: {e}")
        await message.answer(f"Ошибка при сохранении: {e}")

    await state.clear()


# ==================== ОТПРАВКА СООБЩЕНИЙ ====================

@router.callback_query(F.data == "admin_send_message")
async def admin_send_message_menu(callback: types.CallbackQuery):
    """Меню отправки сообщений"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="👤 Пользователю", callback_data="admin_send_to_user"))
    builder.row(InlineKeyboardButton(text="👥 Группе", callback_data="admin_send_to_group"))
    builder.row(InlineKeyboardButton(text="🌐 Всем пользователям", callback_data="admin_send_to_all"))
    builder.row(InlineKeyboardButton(text="← Назад", callback_data="admin"))

    text = (
        "<b>📨 Отправить сообщение</b>\n\n"
        "Выберите получателя сообщения:"
    )

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    await callback.answer()


@router.callback_query(F.data == "admin_send_to_user")
async def admin_send_to_user_select(callback: types.CallbackQuery):
    """Выбор пользователя для отправки сообщения"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    # Получаем всех пользователей из БД
    users_cursor = chats_col.aggregate([
        {"$match": {"chat_type": "private"}},
        {"$group": {"_id": "$user_id", "chat_id": {"$first": "$chat_id"}, "title": {"$first": "$title"}}}
    ])
    users = await users_cursor.to_list(length=100)

    text = "<b>👤 Отправка сообщения пользователю</b>\n\n"
    if not users:
        text += "Нет сохраненных пользователей."
    else:
        text += f"Всего пользователей: {len(users)}\n\nВыберите пользователя:\n\n"

    builder = InlineKeyboardBuilder()
    for user in users[:20]:
        user_id = user.get('_id', '')
        title = user.get('title', 'Без имени')
        builder.row(InlineKeyboardButton(
            text=f"👤 {title[:30]}",
            callback_data=f"admin_send_user_{user_id}"
        ))

    builder.row(InlineKeyboardButton(text="← Назад", callback_data="admin_send_message"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("admin_send_user_"))
async def admin_send_user_prep(callback: types.CallbackQuery, state: FSMContext):
    """Подготовка к отправке сообщения пользователю"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    user_id = callback.data.replace("admin_send_user_", "")
    await state.update_data(
        recipient_type="user",
        recipient_id=user_id,
        last_message_id=callback.message.message_id,
        last_chat_id=callback.message.chat.id
    )
    await state.set_state(AdminStates.wait_message_text)

    text = (
        f"<b>📨 Отправка сообщения пользователю</b>\n\n"
        f"Получатель ID: <code>{user_id}</code>\n\n"
        f"Введите текст сообщения:"
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_keyboard("admin_send_message"))
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    await callback.answer()


@router.callback_query(F.data == "admin_send_to_group")
async def admin_send_to_group_select(callback: types.CallbackQuery):
    """Выбор группы для отправки сообщения"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    groups = await chats_col.find({"chat_type": {"$in": ["group", "supergroup"]}}).to_list(length=100)

    text = "<b>👥 Отправка сообщения группе</b>\n\n"
    if not groups:
        text += "Нет сохраненных групп."
    else:
        text += f"Всего групп: {len(groups)}\n\nВыберите группу:\n\n"

    builder = InlineKeyboardBuilder()
    for group in groups[:20]:
        chat_id = group.get('chat_id', '')
        title = group.get('title', 'Без названия')
        builder.row(InlineKeyboardButton(
            text=f"👥 {title[:30]}",
            callback_data=f"admin_send_group_{chat_id}"
        ))

    builder.row(InlineKeyboardButton(text="← Назад", callback_data="admin_send_message"))

    try:
        await callback.message.edit_text(text, reply_markup=builder.as_markup(), parse_mode="HTML")
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    await callback.answer()


@router.callback_query(F.data.startswith("admin_send_group_"))
async def admin_send_group_prep(callback: types.CallbackQuery, state: FSMContext):
    """Подготовка к отправке сообщения группе"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    chat_id = callback.data.replace("admin_send_group_", "")
    await state.update_data(
        recipient_type="group",
        recipient_id=chat_id,
        last_message_id=callback.message.message_id,
        last_chat_id=callback.message.chat.id
    )
    await state.set_state(AdminStates.wait_message_text)

    text = (
        f"<b>📨 Отправка сообщения группе</b>\n\n"
        f"Получатель ID: <code>{chat_id}</code>\n\n"
        f"Введите текст сообщения:"
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_keyboard("admin_send_message"))
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    await callback.answer()


@router.callback_query(F.data == "admin_send_to_all")
async def admin_send_to_all_prep(callback: types.CallbackQuery, state: FSMContext):
    """Подготовка к отправке сообщения всем"""
    if not await check_admin_access(callback):
        await callback.answer()
        return

    await state.update_data(
        recipient_type="all",
        recipient_id=None,
        last_message_id=callback.message.message_id,
        last_chat_id=callback.message.chat.id
    )
    await state.set_state(AdminStates.wait_message_text)

    text = (
        f"<b>🌐 Отправка сообщения всем пользователям</b>\n\n"
        f"Введите текст сообщения:\n\n"
        f"<i>Сообщение будет отправлено всем пользователям, которые взаимодействовали с ботом.</i>"
    )

    try:
        await callback.message.edit_text(text, parse_mode="HTML", reply_markup=get_cancel_keyboard("admin_send_message"))
    except TelegramBadRequest as e:
        if "message is not modified" in str(e):
            pass
        else:
            raise
    await callback.answer()


@router.message(AdminStates.wait_message_text, F.text)
async def process_admin_message_text(message: types.Message, state: FSMContext):
    """Отправка сообщения от имени бота"""
    from common import get_bot_ref
    
    data = await state.get_data()
    recipient_type = data.get('recipient_type')
    recipient_id = data.get('recipient_id')
    last_message_id = data.get('last_message_id')
    last_chat_id = data.get('last_chat_id')
    message_text = message.text

    try:
        await message.delete()
    except Exception:
        pass

    bot = get_bot_ref()
    if not bot:
        try:
            await bot.edit_message_text(
                chat_id=last_chat_id,
                message_id=last_message_id,
                text="❌ Ошибка: бот не инициализирован",
                reply_markup=get_cancel_keyboard("admin_send_message"),
                parse_mode="HTML"
            )
        except Exception:
            await message.answer("❌ Ошибка: бот не инициализирован")
        await state.clear()
        return

    success_count = 0
    fail_count = 0

    try:
        if recipient_type == "user":
            # Отправка конкретному пользователю
            try:
                await bot.send_message(chat_id=recipient_id, text=message_text, parse_mode="HTML")
                success_count = 1
                result_text = f"✅ Сообщение отправлено пользователю ID: <code>{recipient_id}</code>"
            except Exception as e:
                fail_count = 1
                result_text = f"❌ Не удалось отправить сообщение: {e}"

        elif recipient_type == "group":
            # Отправка конкретной группе
            try:
                await bot.send_message(chat_id=recipient_id, text=message_text, parse_mode="HTML")
                success_count = 1
                result_text = f"✅ Сообщение отправлено группе ID: <code>{recipient_id}</code>"
            except Exception as e:
                fail_count = 1
                result_text = f"❌ Не удалось отправить сообщение: {e}"

        elif recipient_type == "all":
            # Отправка всем пользователям
            users_cursor = chats_col.aggregate([
                {"$match": {"chat_type": "private"}},
                {"$group": {"_id": "$user_id"}}
            ])
            users = await users_cursor.to_list(length=1000)

            for user in users:
                user_id = user.get('_id')
                try:
                    await bot.send_message(chat_id=user_id, text=message_text, parse_mode="HTML")
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
                    fail_count += 1
                await asyncio.sleep(0.05)  # Небольшая задержка чтобы не получить бан

            result_text = (
                f"📨 Рассылка завершена!\n\n"
                f"✅ Успешно: {success_count}\n"
                f"❌ Ошибок: {fail_count}\n"
                f"📊 Всего: {success_count + fail_count}"
            )

        # Редактируем старое сообщение вместо отправки нового
        try:
            await bot.edit_message_text(
                chat_id=last_chat_id,
                message_id=last_message_id,
                text=result_text,
                reply_markup=get_cancel_keyboard("admin_send_message"),
                parse_mode="HTML"
            )
        except TelegramBadRequest as e:
            if "message is not modified" in str(e):
                pass
            else:
                raise

    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения: {e}")
        try:
            await bot.edit_message_text(
                chat_id=last_chat_id,
                message_id=last_message_id,
                text=f"❌ Ошибка при отправке: {e}",
                reply_markup=get_cancel_keyboard("admin_send_message"),
                parse_mode="HTML"
            )
        except Exception:
            await message.answer(f"❌ Ошибка при отправке: {e}")

    await state.clear()