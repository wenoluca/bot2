"""
Storage: sessions, daily counter, admin data, granted users, broadcast list.
"""

import json
import os
import random
import secrets
import string
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


# ── Granted users ────────────────────────────────────────────────────────────

def grant_analysis(username: str, tier: str):
    """Grant by username (admin use)."""
    username = username.lstrip("@").lower()
    data = _load()
    data.setdefault("granted", {})[username] = tier
    _save(data)


def grant_by_chat_id(chat_id: int, tier: str):
    """Grant by Telegram chat_id (self-activation after payment)."""
    data = _load()
    data.setdefault("granted_by_id", {})[str(chat_id)] = tier
    _save(data)


def consume_grant(username: str) -> Optional[str]:
    """Returns tier and removes grant if the user has one (by username), else None."""
    username = username.lstrip("@").lower()
    data = _load()
    tier = data.get("granted", {}).pop(username, None)
    if tier:
        _save(data)
    return tier


def consume_grant_by_chat_id(chat_id: int) -> Optional[str]:
    """Returns tier and removes grant if the user has one (by chat_id), else None."""
    data = _load()
    tier = data.get("granted_by_id", {}).pop(str(chat_id), None)
    if tier:
        _save(data)
    return tier


def get_grant(username: str) -> Optional[str]:
    """Check if user has a grant without consuming it."""
    username = username.lstrip("@").lower()
    return _load().get("granted", {}).get(username)


def has_grant_by_chat_id(chat_id: int) -> Optional[str]:
    """Check if user has a chat_id grant without consuming."""
    return _load().get("granted_by_id", {}).get(str(chat_id))


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


# ── Referral system ───────────────────────────────────────────────────────────

def _gen_ref_code(length: int = 8) -> str:
    """Generate a random alphanumeric referral code."""
    chars = string.ascii_lowercase + string.digits
    return "".join(secrets.choice(chars) for _ in range(length))


def create_referral(name: str, access_usernames: list = None) -> str:
    """
    Create a referral with a friendly name and a random code.
    Returns the generated random code.
    access_usernames — list of usernames (without @) who can see stats.
    """
    name = name.strip()
    data = _load()
    refs = data.setdefault("referrals", {})
    while True:
        code = _gen_ref_code()
        if code not in refs:
            break
    refs[code] = {
        "name": name,
        "created_at": date.today().isoformat(),
        "visitors": [],
        "purchases": [],
        "access_users": [u.lower().lstrip("@") for u in (access_usernames or [])],
    }
    _save(data)
    return code


def delete_referral(name_or_code: str) -> bool:
    """Delete a referral by its friendly name or random code. Returns False if not found."""
    val = name_or_code.strip()
    data = _load()
    refs = data.get("referrals", {})
    # Try exact code match first
    if val in refs:
        del refs[val]
        _save(data)
        return True
    # Try name match (case-insensitive)
    for code, ref in list(refs.items()):
        if ref.get("name", "").lower() == val.lower():
            del refs[code]
            _save(data)
            return True
    return False


def referral_exists(code: str) -> bool:
    code = code.strip()
    return code in _load().get("referrals", {})


def track_referral_visit(name: str, user_id: int) -> bool:
    """Track a unique visitor. Returns True if this is a new visitor."""
    name = name.lower().strip()
    data = _load()
    refs = data.get("referrals", {})
    if name not in refs:
        return False
    visitors = refs[name].setdefault("visitors", [])
    if user_id not in visitors:
        visitors.append(user_id)
        _save(data)
        return True
    return False


def set_user_referral(user_id: int, name: str):
    """Associate a user with a referral source."""
    data = _load()
    data.setdefault("user_referral", {})[str(user_id)] = name.lower().strip()
    _save(data)


def get_user_referral(user_id: int) -> Optional[str]:
    """Get the referral name associated with a user, if any."""
    return _load().get("user_referral", {}).get(str(user_id))


def track_referral_purchase(user_id: int, tier: str):
    """Track a purchase and attribute it to the user's referral source."""
    ref_name = get_user_referral(user_id)
    if not ref_name:
        return
    data = _load()
    refs = data.get("referrals", {})
    if ref_name not in refs:
        return
    refs[ref_name].setdefault("purchases", []).append({
        "user_id": user_id,
        "tier": tier,
        "date": date.today().isoformat(),
    })
    _save(data)


def get_all_referrals() -> dict:
    return _load().get("referrals", {})


def get_referrals_for_user(username: str) -> dict:
    """Return referrals where username is in access_users."""
    username = username.lower().lstrip("@")
    refs = _load().get("referrals", {})
    return {code: ref for code, ref in refs.items()
            if username in ref.get("access_users", [])}
