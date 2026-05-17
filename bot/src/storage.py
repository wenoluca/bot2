"""
Storage: sessions, daily counter, admin data, granted users, broadcast list.
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
        json.dump(data, f, ensure_ascii=False)


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
    data = _load()
    today = date.today().isoformat()
    daily = data.setdefault("daily", {"date": "", "count": 0, "offset": 0})
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


# ── Username → chat_id mapping ────────────────────────────────────────────────

def save_user_chat_id(username: str, chat_id: int):
    """Save username → chat_id so we can notify users by username."""
    if not username:
        return
    username = username.lower().lstrip("@")
    data = _load()
    data.setdefault("username_to_chat", {})[username] = chat_id
    _save(data)


def get_chat_id_by_username(username: str) -> Optional[int]:
    username = username.lower().lstrip("@")
    return _load().get("username_to_chat", {}).get(username)


# ── Granted users (admin manually approves after payment) ────────────────────

def grant_analysis(username: str, tier: str):
    """Admin grants one free analysis (tier: 'brief' | 'full') to a user."""
    username = username.lstrip("@").lower()
    data = _load()
    data.setdefault("granted", {})[username] = tier
    _save(data)


def consume_grant(username: str) -> Optional[str]:
    """Returns tier and removes grant if the user has one, else None."""
    username = username.lstrip("@").lower()
    data = _load()
    tier = data.get("granted", {}).pop(username, None)
    if tier:
        _save(data)
    return tier


def get_grant(username: str) -> Optional[str]:
    """Check if user has a grant without consuming it."""
    username = username.lstrip("@").lower()
    return _load().get("granted", {}).get(username)


# ── Broadcast list (all users who started the bot) ───────────────────────────

def register_user(chat_id: int, username: str = ""):
    data = _load()
    known = set(data.get("user_ids", []))
    known.add(chat_id)
    data["user_ids"] = list(known)
    if username:
        data.setdefault("username_to_chat", {})[username.lower().lstrip("@")] = chat_id
    _save(data)


def get_all_user_ids() -> list:
    return _load().get("user_ids", [])
