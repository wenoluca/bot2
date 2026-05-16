"""
Storage: pending photo sessions + daily analysis counter + admin chat ID.
"""

import json
import os
import random
from datetime import date
from typing import Optional

STORAGE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "storage.json")


def _load() -> dict:
    try:
        os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(data: dict):
    os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)


# ── Pending photo ─────────────────────────────────────────────────────────────

def save_pending_photo(user_id: int, file_id: str):
    data = _load()
    data.setdefault("pending_photos", {})[str(user_id)] = file_id
    _save(data)


def get_pending_photo(user_id: int) -> Optional[str]:
    return _load().get("pending_photos", {}).get(str(user_id))


def clear_pending_photo(user_id: int):
    data = _load()
    data.setdefault("pending_photos", {}).pop(str(user_id), None)
    _save(data)


# ── Daily analysis counter ────────────────────────────────────────────────────

def increment_daily_count():
    """Call once after a successful analysis."""
    data = _load()
    today = date.today().isoformat()
    daily = data.setdefault("daily", {"date": "", "count": 0, "offset": 0})
    if daily.get("date") != today:
        daily["date"] = today
        daily["count"] = 0
        daily["offset"] = random.randint(40, 100)
    daily["count"] += 1
    _save(data)


def get_displayed_daily_count() -> int:
    """
    Returns today's real count + a fixed random offset (40–100) that is
    set ONCE per day and persisted — never changes on bot restart.
    """
    data = _load()
    today = date.today().isoformat()
    daily = data.setdefault("daily", {"date": "", "count": 0, "offset": 0})

    # Initialise a new day (only once per calendar day)
    if daily.get("date") != today:
        daily["date"] = today
        daily["count"] = 0
        daily["offset"] = random.randint(40, 100)
        _save(data)

    return daily.get("count", 0) + daily.get("offset", 70)


# ── Admin chat ID ─────────────────────────────────────────────────────────────

def save_admin_chat_id(chat_id: int):
    data = _load()
    data["admin_chat_id"] = chat_id
    _save(data)


def get_admin_chat_id() -> Optional[int]:
    return _load().get("admin_chat_id")
