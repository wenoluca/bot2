"""
Simple in-memory + file-based storage for pending payments and user state.
Persists pending photo analysis requests across restarts using a JSON file.
"""

import json
import os
from typing import Optional

STORAGE_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "storage.json")


def _load() -> dict:
    try:
        os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
        with open(STORAGE_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"pending_photos": {}}


def _save(data: dict):
    os.makedirs(os.path.dirname(STORAGE_FILE), exist_ok=True)
    with open(STORAGE_FILE, "w") as f:
        json.dump(data, f)


def save_pending_photo(user_id: int, file_id: str):
    data = _load()
    data.setdefault("pending_photos", {})[str(user_id)] = file_id
    _save(data)


def get_pending_photo(user_id: int) -> Optional[str]:
    data = _load()
    return data.get("pending_photos", {}).get(str(user_id))


def clear_pending_photo(user_id: int):
    data = _load()
    data.setdefault("pending_photos", {}).pop(str(user_id), None)
    _save(data)
