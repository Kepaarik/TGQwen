from datetime import datetime
from config import MOSCOW_TZ
from database.connection import events_col, settings_col
from bson import ObjectId

async def get_all_events():
    cursor = events_col.find().sort("created_at", -1)
    return await cursor.to_list(length=100)

async def add_event(user_id: int, user_name: str, date_str: str, description: str, recurrence: str = None):
    event_doc = {
        "user_id": str(user_id),
        "user_name": user_name,
        "date_str": date_str,
        "description": description,
        "recurrence": recurrence,
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
    await events_col.delete_one({"_id": ObjectId(event_id)})

async def get_event_by_id(event_id: str):
    return await events_col.find_one({"_id": ObjectId(event_id)})

async def update_event(event_id: str, updates: dict):
    await events_col.update_one({"_id": ObjectId(event_id)}, {"$set": updates})
