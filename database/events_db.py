from datetime import datetime, time
from config import MOSCOW_TZ
from database.connection import events_col, settings_col, chats_col
from bson import ObjectId

async def get_all_events():
    cursor = events_col.find().sort("created_at", -1)
    return await cursor.to_list(length=100)

async def add_event(user_id: int, user_name: str, date_str: str, description: str, recurrence: str = None, greeting_time: str = "09:00", chats: list = None):
    event_doc = {
        "user_id": str(user_id),
        "user_name": user_name,
        "date_str": date_str,
        "description": description,
        "recurrence": recurrence,
        "greeting_time": greeting_time,  # Время отправки поздравления в формате ЧЧ:ММ
        "chats": chats or [],  # Список ID чатов для отображения уведомлений
        "last_check_time": None,  # Время последней проверки события
        "created_at": datetime.now(MOSCOW_TZ)
    }
    await events_col.insert_one(event_doc)

async def get_last_event_check():
    return await settings_col.find_one({"key": "last_event_check"})

async def update_last_event_check(date_str: str):
    await settings_col.update_one(
        {"key": "last_event_check"}, 
        {"$set": {"value": date_str}}, 
        upsert=True
    )

async def delete_event(event_id: str):
    try:
        await events_col.delete_one({"_id": ObjectId(event_id)})
    except Exception:
        # Если event_id уже является ObjectId или некорректен
        await events_col.delete_one({"_id": event_id})

async def get_event_by_id(event_id: str):
    try:
        return await events_col.find_one({"_id": ObjectId(event_id)})
    except Exception:
        return await events_col.find_one({"_id": event_id})

async def update_event(event_id: str, updates: dict):
    try:
        await events_col.update_one({"_id": ObjectId(event_id)}, {"$set": updates})
    except Exception:
        await events_col.update_one({"_id": event_id}, {"$set": updates})

async def get_greeting_time(user_id: str, event_id: str) -> str:
    """Получить время отправки поздравления для события"""
    event = await get_event_by_id(event_id)
    if event:
        return event.get("greeting_time", "09:00")
    return "09:00"

async def set_greeting_time(event_id: str, greeting_time: str):
    """Установить время отправки поздравления для события"""
    try:
        await events_col.update_one({"_id": ObjectId(event_id)}, {"$set": {"greeting_time": greeting_time}})
    except Exception:
        await events_col.update_one({"_id": event_id}, {"$set": {"greeting_time": greeting_time}})

async def set_event_last_check_time(event_id: str, check_time: str):
    """Установить время последней проверки события"""
    try:
        await events_col.update_one({"_id": ObjectId(event_id)}, {"$set": {"last_check_time": check_time}})
    except Exception:
        await events_col.update_one({"_id": event_id}, {"$set": {"last_check_time": check_time}})

async def get_event_last_check_time(event_id: str) -> str:
    """Получить время последней проверки события"""
    event = await get_event_by_id(event_id)
    if event:
        return event.get("last_check_time", "Не проверялось")
    return "Не проверялось"

async def get_greeting_status(user_id: str, event_id: str, date_str: str):
    """Проверить, было ли уже поздравление с этим событием сегодня"""
    record = await settings_col.find_one({
        "key": "greeting_status",
        "user_id": str(user_id),
        "event_id": event_id,
        "date_str": date_str
    })
    return record is not None

async def set_greeting_status(user_id: str, event_id: str, date_str: str):
    """Отметить, что событие было поздравлено сегодня"""
    await settings_col.update_one(
        {
            "key": "greeting_status",
            "user_id": str(user_id),
            "event_id": event_id,
            "date_str": date_str
        },
        {"$set": {"greeted_at": datetime.now(MOSCOW_TZ)}},
        upsert=True
    )

async def get_event_chats(event_id: str) -> list:
    """Получить список чатов для события"""
    event = await get_event_by_id(event_id)
    if event:
        return event.get("chats", [])
    return []

async def set_event_chats(event_id: str, chats: list):
    """Установить список чатов для события"""
    try:
        await events_col.update_one({"_id": ObjectId(event_id)}, {"$set": {"chats": chats}})
    except Exception:
        await events_col.update_one({"_id": event_id}, {"$set": {"chats": chats}})

async def add_event_chat(event_id: str, chat_id: str):
    """Добавить чат к списку чатов события"""
    try:
        await events_col.update_one({"_id": ObjectId(event_id)}, {"$addToSet": {"chats": chat_id}})
    except Exception:
        await events_col.update_one({"_id": event_id}, {"$addToSet": {"chats": chat_id}})

async def remove_event_chat(event_id: str, chat_id: str):
    """Удалить чат из списка чатов события"""
    try:
        await events_col.update_one({"_id": ObjectId(event_id)}, {"$pull": {"chats": chat_id}})
    except Exception:
        await events_col.update_one({"_id": event_id}, {"$pull": {"chats": chat_id}})

async def clear_old_greeting_statuses(user_id: str, current_date_str: str):
    """Очистить старые записи о поздравлениях (оставить только за текущую дату)"""
    await settings_col.delete_many({
        "key": "greeting_status",
        "user_id": str(user_id),
        "date_str": {"$ne": current_date_str}
    })

async def save_user_chat(user_id: int, chat_id: str, chat_type: str, title: str = None, username: str = None):
    """Сохранить информацию о чате, в котором находится пользователь"""
    chat_doc = {
        "user_id": str(user_id),
        "chat_id": chat_id,
        "chat_type": chat_type,
        "title": title,
        "username": username,
        "updated_at": datetime.now(MOSCOW_TZ)
    }
    await chats_col.update_one(
        {"user_id": str(user_id), "chat_id": chat_id},
        {"$set": chat_doc},
        upsert=True
    )

async def get_user_chats(user_id: int) -> list:
    """Получить все чаты пользователя, в которые бот может писать"""
    cursor = chats_col.find({"user_id": str(user_id)}).sort("updated_at", -1)
    return await cursor.to_list(length=100)

async def remove_user_chat(user_id: int, chat_id: str):
    """Удалить чат из списка чатов пользователя"""
    await chats_col.delete_one({"user_id": str(user_id), "chat_id": chat_id})

async def get_chat_display_info(chat_id: str, chat_type: str, title: str = None, username: str = None) -> str:
    """Получить отображаемое имя для чата"""
    if chat_type == "private":
        # Для личного чата используем username или имя пользователя
        if username:
            return f"@{username}"
        elif title:
            return title
        else:
            return f"Личный чат ({chat_id})"
    else:
        # Для групп используем название группы или ID
        if title:
            return title
        else:
            return f"Группа ({chat_id})"
