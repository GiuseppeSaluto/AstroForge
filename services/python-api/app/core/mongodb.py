from pymongo import MongoClient
from pymongo.errors import PyMongoError
from datetime import datetime

client  = MongoClient("MONGODB_URI")
db = client["MONGO_DB_NASA"]

def save_nasa_feed(data: dict):
    db.nasa_feeds.insert_one({
        "data": data,
        "imported_at": datetime.now(datetime.timezone.utc)
    })