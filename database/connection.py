from motor.motor_asyncio import AsyncIOMotorClient
from config import MONGO_URL

client = AsyncIOMotorClient(MONGO_URL)
db = client.marathon_db
users_col = db.users
events_col = db.events
settings_col = db.settings
