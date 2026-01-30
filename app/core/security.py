import secrets

def gen_api_key(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(24)}"
