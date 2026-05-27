import os
import ssl
from datetime import datetime

import certifi
from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.collection import ReturnDocument
from pymongo.server_api import ServerApi


MONGO_URI = os.environ.get(
    "MONGODB_URI",
    "mongodb+srv://facesense:facesenseAI@facesense.bmebkyz.mongodb.net/?appName=FaceSense",
)
MONGO_DB_NAME = os.environ.get("MONGODB_DB", "facesense")

_client = None
_db = None
_users = None
_history = None
_counters = None


def connect_db():
    global _client, _db, _users, _history, _counters

    # Try multiple connection strategies
    strategies = [
        # Strategy 1: certifi CA + ServerApi
        lambda: MongoClient(
            MONGO_URI,
            server_api=ServerApi("1"),
            tlsCAFile=certifi.where(),
        ),
        # Strategy 2: certifi only
        lambda: MongoClient(
            MONGO_URI,
            tlsCAFile=certifi.where(),
        ),
        # Strategy 3: disable cert verification (last resort)
        lambda: MongoClient(
            MONGO_URI,
            tls=True,
            tlsAllowInvalidCertificates=True,
        ),
    ]

    last_error = None
    for i, strategy in enumerate(strategies, 1):
        try:
            print(f"🔄 Trying connection strategy {i}...")
            client = strategy()
            client.admin.command("ping")
            _client = client
            _db = _client[MONGO_DB_NAME]
            _users = _db["users"]
            _history = _db["emotion_history"]
            _counters = _db["counters"]
            print(f"✅ MongoDB Connected (strategy {i})")
            return  # success
        except Exception as e:
            print(f"❌ Strategy {i} failed: {e}")
            last_error = e

    # All strategies failed
    raise RuntimeError(f"Could not connect to MongoDB after all attempts. Last error: {last_error}")


connect_db()


def _next_id(counter_name: str) -> int:
    doc = _counters.find_one_and_update(
        {"_id": counter_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(doc["seq"])


def _strip_mongo_id(doc: dict | None):
    if not doc:
        return None
    out = dict(doc)
    out.pop("_id", None)
    return out


def init_db() -> None:
    if _users is None or _history is None:
        raise RuntimeError("Database not connected. Call connect_db() first.")
    _users.create_index([("id", ASCENDING)], unique=True)
    _users.create_index([("phone", ASCENDING)], unique=True)
    _history.create_index([("id", ASCENDING)], unique=True)
    _history.create_index([("user_id", ASCENDING), ("id", DESCENDING)])


def get_user_by_phone(phone: str):
    return _strip_mongo_id(_users.find_one({"phone": phone}))


def get_user_by_id(user_id: int):
    return _strip_mongo_id(_users.find_one({"id": int(user_id)}))


def create_user(name: str, phone: str, occupation: str, password_hash: str) -> int:
    user_id = _next_id("users")
    _users.insert_one(
        {
            "id": user_id,
            "name": name,
            "phone": phone,
            "occupation": occupation,
            "password": password_hash,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
    )
    return user_id


def save_emotion_history(user_id: int, emotion: str, suggestion: str, source: str | None = None) -> None:
    history_id = _next_id("emotion_history")
    _history.insert_one(
        {
            "id": history_id,
            "user_id": int(user_id),
            "emotion": str(emotion),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "suggestion": suggestion,
            "source": source or "manual",
        }
    )


def get_recent_emotion_history(user_id: int, limit: int = 8):
    rows = _history.find(
        {"user_id": int(user_id)},
        {"_id": 0, "emotion": 1, "timestamp": 1, "source": 1},
    ).sort("id", DESCENDING).limit(int(limit))
    out = []
    for row in rows:
        row["source"] = row.get("source") or "unknown"
        out.append(row)
    return out


def get_emotion_frequency(user_id: int):
    pipeline = [
        {"$match": {"user_id": int(user_id)}},
        {"$project": {"emotion_lower": {"$toLower": "$emotion"}}},
        {"$group": {"_id": "$emotion_lower", "freq": {"$sum": 1}}},
    ]
    data = _history.aggregate(pipeline)
    return {str(item["_id"]): int(item["freq"]) for item in data if item.get("_id")}


def get_emotion_dates(user_id: int):
    rows = _history.find(
        {"user_id": int(user_id)},
        {"_id": 0, "timestamp": 1},
    ).sort("id", DESCENDING)

    unique_days = []
    seen = set()
    for row in rows:
        ts = str(row.get("timestamp") or "").strip()
        if not ts:
            continue
        day = ts.split(" ", 1)[0]
        if day and day not in seen:
            seen.add(day)
            unique_days.append(day)
    return unique_days