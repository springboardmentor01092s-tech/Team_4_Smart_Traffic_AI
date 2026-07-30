from pymongo import MongoClient
from pymongo.server_api import ServerApi
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class MongoDB:
    client: MongoClient = None
    db = None

mongodb_client = MongoDB()

def connect_to_mongo():
    try:
        mongodb_client.client = MongoClient(
            settings.MONGODB_URI,
            server_api=ServerApi('1'),
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=5000
        )
        mongodb_client.db = mongodb_client.client[settings.MONGODB_DB_NAME]
        mongodb_client.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB Atlas!")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")

def close_mongo_connection():
    if mongodb_client.client:
        mongodb_client.client.close()
        logger.info("MongoDB connection closed.")

def get_mongo_db():
    return mongodb_client.db
