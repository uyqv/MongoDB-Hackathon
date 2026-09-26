"""Atlas access shared by both branches. OWNER: Andrew. Do not edit on `david`."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from functools import lru_cache

from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.database import Database

from harness.contracts import DB_NAME_DEFAULT

load_dotenv()


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@lru_cache(maxsize=1)
def get_client() -> MongoClient:
    uri = os.environ["MONGODB_URI"]
    return MongoClient(uri, appname="second-shift", serverSelectionTimeoutMS=10_000)


def get_db(name: str | None = None) -> Database:
    """DB_NAME in .env picks the database. Andrew: second_shift. David dev: second_shift_david."""
    return get_client()[name or os.environ.get("DB_NAME", DB_NAME_DEFAULT)]


def log_event(db: Database, campaign_id: str, type_: str, payload: dict | None = None,
              worker_id: str | None = None) -> None:
    """Append-only audit/UI event. Never used as the source of truth for results."""
    db.events.insert_one({
        "campaign_id": campaign_id,
        "ts": now_iso(),
        "type": type_,
        "worker_id": worker_id,
        "payload": payload or {},
    })
