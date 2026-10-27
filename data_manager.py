"""
data_manager.py
Handles all file-based (JSON) persistence: the side hustle catalog and the
user database. Centralizing I/O here keeps disk access, locking-free
read/write, and error handling in one place.
"""

import json
import os
import uuid
from threading import Lock

from utils import get_logger, DataStoreError
from models import User, SideHustle

logger = get_logger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SIDE_HUSTLES_FILE = os.path.join(DATA_DIR, "side_hustles.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

_write_lock = Lock()


def _read_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        logger.error("Failed to read %s: %s", path, exc)
        raise DataStoreError(f"Could not read data file: {os.path.basename(path)}") from exc


def _write_json(path, data):
    try:
        with _write_lock:
            tmp_path = path + ".tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            os.replace(tmp_path, path)
    except OSError as exc:
        logger.error("Failed to write %s: %s", path, exc)
        raise DataStoreError(f"Could not save data file: {os.path.basename(path)}") from exc


class SideHustleRepository:
    """Read-only access to the side hustle catalog."""

    def __init__(self, path=SIDE_HUSTLES_FILE):
        self.path = path
        self._cache = None

    def load_all(self):
        if self._cache is None:
            raw = _read_json(self.path, default=[])
            self._cache = [SideHustle.from_dict(item) for item in raw]
            logger.info("Loaded %d side hustles from catalog.", len(self._cache))
        return self._cache

    def get_by_id(self, hustle_id):
        for hustle in self.load_all():
            if hustle.id == hustle_id:
                return hustle
        return None

    def categories(self):
        return sorted({h.category for h in self.load_all()})


class UserRepository:
    """CRUD access to the user store."""

    def __init__(self, path=USERS_FILE):
        self.path = path

    def _load_raw(self):
        return _read_json(self.path, default=[])

    def load_all(self):
        return [User.from_dict(d) for d in self._load_raw()]

    def get_by_id(self, user_id):
        for d in self._load_raw():
            if d["user_id"] == user_id:
                return User.from_dict(d)
        return None

    def get_by_username(self, username):
        username_lower = username.strip().lower()
        for d in self._load_raw():
            if d["username"].strip().lower() == username_lower:
                return User.from_dict(d)
        return None

    def get_by_email(self, email):
        email_lower = email.strip().lower()
        for d in self._load_raw():
            if d["email"].strip().lower() == email_lower:
                return User.from_dict(d)
        return None

    def create(self, user: User):
        records = self._load_raw()
        if not user.user_id:
            user.user_id = str(uuid.uuid4())
        records.append(user.to_dict())
        _write_json(self.path, records)
        logger.info("Created user %s (%s)", user.username, user.user_id)
        return user

    def update(self, user: User):
        records = self._load_raw()
        found = False
        for i, d in enumerate(records):
            if d["user_id"] == user.user_id:
                records[i] = user.to_dict()
                found = True
                break
        if not found:
            raise DataStoreError(f"User {user.user_id} not found for update.")
        _write_json(self.path, records)
        logger.info("Updated user %s", user.username)
        return user
