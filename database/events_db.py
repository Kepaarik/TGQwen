from datetime import datetime, time
from config import MOSCOW_TZ
from database.connection import events_col, settings_col
from bson import ObjectId

async def get_all_events():
    cursor = events_col.find().sort("created_at", -1)
    return await cursor.to_list(length=100)

async def add_event(user_id: int, user_name: str, date_str: str, description: str, recurrence: str = None, greeting_time: str = "09:00"):
    event_doc = {
        "user_id": str(user_id),
        "user_name": user_name,
        "date_str": date_str,
        "description": description,
        "recurrence": recurrence,
        "greeting_time": greeting_time,  # Время отправки поздравления в формате ЧЧ:ММ
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

async def clear_old_greeting_statuses(user_id: str, current_date_str: str):
    """Очистить старые записи о поздравлениях (оставить только за текущую дату)"""
    await settings_col.delete_many({
        "key": "greeting_status",
        "user_id": str(user_id),
        "date_str": {"$ne": current_date_str}
    })
