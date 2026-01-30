import base64
import datetime as dt
import hashlib
import hmac
import os
import secrets
from dataclasses import dataclass

from .config import settings


# ===== Password hashing (dependency-free) =====

PBKDF2_ALG = "sha256"


def hash_password(password: str) -> str:
    """Return a PBKDF2 hash string.

    Format: pbkdf2_sha256$<iterations>$<salt_b64>$<dk_b64>
    """
    if not isinstance(password, str) or len(password) < 6:
        raise ValueError("password too short")

    salt = os.urandom(16)
    iters = int(settings.PASSWORD_PBKDF2_ITERATIONS)
    dk = hashlib.pbkdf2_hmac(PBKDF2_ALG, password.encode("utf-8"), salt, iters, dklen=32)
    return "pbkdf2_sha256$%d$%s$%s" % (
        iters,
        base64.urlsafe_b64encode(salt).decode("ascii").rstrip("="),
        base64.urlsafe_b64encode(dk).decode("ascii").rstrip("="),
    )


def verify_password(password: str, stored: str) -> bool:
    try:
        kind, iters_s, salt_b64, dk_b64 = stored.split("$", 3)
        if kind != "pbkdf2_sha256":
            return False
        iters = int(iters_s)
        salt = base64.urlsafe_b64decode(_pad_b64(salt_b64))
        dk_stored = base64.urlsafe_b64decode(_pad_b64(dk_b64))
        dk = hashlib.pbkdf2_hmac(PBKDF2_ALG, password.encode("utf-8"), salt, iters, dklen=len(dk_stored))
        return hmac.compare_digest(dk, dk_stored)
    except Exception:
        return False


def _pad_b64(s: str) -> str:
    return s + "=" * (-len(s) % 4)


# ===== Session token =====

def new_token() -> str:
    # URL-safe token for Bearer auth
    return secrets.token_urlsafe(32)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def expires_at(hours: int | None = None) -> dt.datetime:
    h = int(hours or settings.AUTH_TOKEN_TTL_HOURS)
    return dt.datetime.now(dt.timezone.utc) + dt.timedelta(hours=h)


@dataclass
class AuthResult:
    token: str
    expires_at: dt.datetime
