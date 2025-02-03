import os
import pymongo
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.server_api import ServerApi

class MotorDB():
    def __init__(self):
        mongo_pass = os.getenv("MONGO_DB_PASS")
        conn_str = f"mongodb+srv://Kur0:{mongo_pass}@kur0bot1.b8p3zby.mongodb.net/?retryWrites=true&w=majority"
        self.motor_client = AsyncIOMotorClient(conn_str, server_api=ServerApi("1"))
            
    