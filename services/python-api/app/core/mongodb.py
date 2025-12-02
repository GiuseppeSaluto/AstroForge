from pymongo import MongoClient
from pymongo.errors import PyMongoError

from app.core.config import (
    NASA_API_KEY,
    NASA_BASE_URL,
    NASA_APOD_ENDPOINT,
    NASA_NEO_FEED_ENDPOINT,
    REQUEST_TIMEOUT,
)

class MongoDBClient:
    def __init__(self, uri: str, db_name: str):
        self.uri = uri
        self.db_name = db_name
        self.client = None
        self.db = None

    def connect(self):
        try:
            self.client = MongoClient(self.uri)
            self.db = self.client[self.db_name]
            print("Connected to MongoDB")
        except PyMongoError as e:
            print(f"Error connecting to MongoDB: {e}")

    def get_collection(self, collection_name: str):
        if self.db:
            return self.db[collection_name]
        else:
            raise Exception("Database not connected. Call connect() first.")

    def close(self):
        if self.client:
            self.client.close()
            print("MongoDB connection closed")