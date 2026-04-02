from datetime import datetime
from config import MOSCOW_TZ
from database.connection import users_col

async def add_transaction(user_id: int, user_name: str, amount: float, currency: str, is_income: bool):
    """
    Добавляет транзакцию в БД.
    user_id конвертируется в строку для совместимости со старыми данными.
    """
    val = abs(amount) if is_income else -abs(amount)
    doc = {
        "user_id": str(user_id),
        "user_name": user_name,
        "amount": val,
        "currency": currency,
        "date": datetime.now(MOSCOW_TZ)
    }
    await users_col.insert_one(doc)

async def get_user_history(user_id: int, limit: int = 10):
    cursor = users_col.find({"user_id": str(user_id)}).sort("date", -1).limit(limit)
    return await cursor.to_list(length=limit)

async def get_all_transactions(user_id: int = None):
    query = {"user_id": str(user_id)} if user_id else {}
    cursor = users_col.find(query)
    return await cursor.to_list(length=2000)

async def get_user_last_active_dates():
    cursor = users_col.aggregate([
        {"$group": {"_id": "$user_id", "last_date": {"$max": "$date"}, "n": {"$first": "$user_name"}}}
    ])
    return await cursor.to_list(length=100)
