"""
MongoDB Database Connection and Collection Helpers
Stores owner registration details and food records permanently.
"""

from pymongo import MongoClient, ASCENDING, DESCENDING
from bson.objectid import ObjectId
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Global mongo client and db references
client = None
db = None

def init_db(app):
    """Initialize MongoDB connection and create required indexes."""
    global client, db
    mongo_uri = app.config.get("MONGO_URI", "mongodb://127.0.0.1:27017/")
    db_name = app.config.get("DB_NAME", "food_waste_prediction")
    
    try:
        client = MongoClient(mongo_uri, serverSelectionTimeoutMS=3000)
        # Verify connection
        client.admin.command('ping')
        db = client[db_name]
        logger.info(f"Connected to MongoDB successfully at {mongo_uri}, database: {db_name}")
        
        # Ensure collections exist and setup indexes
        setup_indexes()
        return db
    except Exception as e:
        logger.warning(f"Could not connect to MongoDB at {mongo_uri}: {e}")
        # Return db object anyway so it can attempt connection when MongoDB starts
        if client is not None:
            db = client[db_name]
        return db

def get_db():
    """Retrieve active database instance or reconnect if necessary."""
    global client, db
    if db is None:
        try:
            client = MongoClient("mongodb://127.0.0.1:27017/", serverSelectionTimeoutMS=2000)
            db = client["food_waste_prediction"]
            setup_indexes()
        except Exception as e:
            logger.error(f"Error accessing database: {e}")
    return db

def is_db_connected():
    """Check if MongoDB server is currently reachable."""
    try:
        database = get_db()
        if database is not None and client is not None:
            client.admin.command('ping')
            return True
    except Exception:
        return False
    return False

def setup_indexes():
    """Create indexes for owners and food_records collections."""
    global db
    if db is None:
        return
    try:
        # Unique index on email to prevent duplicate registrations
        db.owners.create_index([("email", ASCENDING)], unique=True)
        # Indexes for fast querying by owner and date
        db.food_records.create_index([("owner_id", ASCENDING), ("food_date", DESCENDING)])
        db.food_records.create_index([("owner_id", ASCENDING), ("food_category", ASCENDING)])
    except Exception as e:
        logger.warning(f"Note on creating indexes: {e}")

# Owner collection helpers
def find_owner_by_email(email):
    database = get_db()
    if database is None:
        return None
    return database.owners.find_one({"email": email.strip().lower()})

def find_owner_by_id(owner_id):
    database = get_db()
    if database is None:
        return None
    try:
        oid = ObjectId(owner_id) if isinstance(owner_id, str) else owner_id
        return database.owners.find_one({"_id": oid})
    except Exception:
        return None

def create_owner(owner_data):
    """
    Insert a new owner into 'owners' collection.
    Expected keys: owner_name, hotel_name, email, phone, password_hash
    """
    database = get_db()
    if database is None:
        raise ConnectionError("MongoDB is not connected")
    
    doc = {
        "owner_name": owner_data["owner_name"].strip(),
        "hotel_name": owner_data["hotel_name"].strip(),
        "email": owner_data["email"].strip().lower(),
        "phone": owner_data.get("phone", "").strip(),
        "password": owner_data["password_hash"],
        "registration_date": datetime.now()
    }
    result = database.owners.insert_one(doc)
    return str(result.inserted_id)

# Food records collection helpers
def insert_food_record(record_data):
    """
    Insert a food record into 'food_records' collection.
    Permanently links record to owner_id.
    """
    database = get_db()
    if database is None:
        raise ConnectionError("MongoDB is not connected")
    
    # Ensure numerical safety and calculations
    prepared = float(record_data.get("quantity_prepared", 0.0))
    consumed = float(record_data.get("quantity_consumed", 0.0))
    wasted = max(0.0, round(prepared - consumed, 2))
    waste_pct = round((wasted / prepared) * 100, 2) if prepared > 0 else 0.0
    
    doc = {
        "owner_id": str(record_data["owner_id"]),
        "food_name": record_data["food_name"].strip(),
        "food_category": record_data["food_category"].strip(),
        "quantity_prepared": prepared,
        "quantity_consumed": consumed,
        "quantity_wasted": wasted,
        "waste_percentage": waste_pct,
        "people_served": int(record_data.get("people_served", 0)),
        "food_date": str(record_data["food_date"]),
        "day_of_week": str(record_data.get("day_of_week", "")),
        "created_date": datetime.now()
    }
    result = database.food_records.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc

def get_owner_food_records(owner_id, filter_date=None, filter_category=None):
    """Retrieve food records belonging only to the specified owner."""
    database = get_db()
    if database is None:
        return []
    
    query = {"owner_id": str(owner_id)}
    if filter_date:
        query["food_date"] = filter_date
    if filter_category and filter_category != "All":
        query["food_category"] = filter_category
        
    cursor = database.food_records.find(query).sort("food_date", DESCENDING)
    records = []
    for doc in cursor:
        doc["_id"] = str(doc["_id"])
        # Ensure waste_percentage is explicitly defined and formatted to avoid Jinja UndefinedError
        if "quantity_wasted" not in doc:
            prep = float(doc.get("quantity_prepared", 0))
            cons = float(doc.get("quantity_consumed", 0))
            doc["quantity_wasted"] = max(0.0, round(prep - cons, 2))
        if "waste_percentage" not in doc:
            prep = float(doc.get("quantity_prepared", 0))
            doc["waste_percentage"] = round((doc["quantity_wasted"] / prep) * 100, 2) if prep > 0 else 0.0
        records.append(doc)
    return records

def get_today_records(owner_id, today_date_str):
    """Get all records added for today's date for this owner."""
    return get_owner_food_records(owner_id, filter_date=today_date_str)
