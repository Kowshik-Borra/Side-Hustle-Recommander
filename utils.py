"""
utils.py
Shared utilities: logging configuration, regex-based validation helpers,
and custom exception classes used across the application.
"""

import logging
import os
import re

# ---------------------------------------------------------------------------
# Logging configuration
# ---------------------------------------------------------------------------
LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(LOG_DIR, "app.log")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger configured with the shared handlers."""
    return logging.getLogger(name)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------
class AppError(Exception):
    """Base class for all application-specific errors."""


class ValidationError(AppError):
    """Raised when user-submitted data fails validation."""


class UserNotFoundError(AppError):
    """Raised when a lookup for a user account fails."""


class DuplicateUserError(AppError):
    """Raised when attempting to register a username/email that already exists."""


class AuthenticationError(AppError):
    """Raised when login credentials are invalid."""


class DataStoreError(AppError):
    """Raised when reading/writing the JSON data store fails."""


# ---------------------------------------------------------------------------
# Regex-based validators
# ---------------------------------------------------------------------------
USERNAME_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{2,19}$")
EMAIL_PATTERN = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
# At least 8 chars, one letter, one digit
PASSWORD_PATTERN = re.compile(r"^(?=.*[A-Za-z])(?=.*\d).{8,}$")


def validate_username(username: str) -> None:
    if not username or not USERNAME_PATTERN.match(username.strip()):
        raise ValidationError(
            "Username must start with a letter and be 3-20 characters "
            "(letters, numbers, underscore only)."
        )


def validate_email(email: str) -> None:
    if not email or not EMAIL_PATTERN.match(email.strip()):
        raise ValidationError("Please enter a valid email address.")


def validate_password(password: str) -> None:
    if not password or not PASSWORD_PATTERN.match(password):
        raise ValidationError(
            "Password must be at least 8 characters long and include "
            "at least one letter and one number."
        )


def parse_comma_list(raw: str) -> list:
    """
    Parse a comma/semicolon separated free-text field (e.g. skills or
    interests) into a clean list of normalized strings using regex.
    """
    if not raw:
        return []
    parts = re.split(r"[,;/]+", raw)
    cleaned = []
    for part in parts:
        item = re.sub(r"\s+", " ", part).strip()
        if item:
            cleaned.append(item)
    return cleaned


def normalize_skill(skill: str) -> str:
    """Lower-case and strip a skill string for case-insensitive comparison."""
    return re.sub(r"\s+", " ", skill.strip().lower())
