"""Opaque random tokens and versioned PBKDF2 hashes, using the standard library."""
import base64
import hashlib
import hmac
import secrets

ITERATIONS = 600_000

def digest(value: str) -> str:
    return hashlib.sha256(value.encode('utf-8')).hexdigest()

def new_token() -> str:
    return secrets.token_urlsafe(32)

def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    value = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, ITERATIONS)
    return 'pbkdf2_sha256$%d$%s$%s' % (ITERATIONS, base64.b64encode(salt).decode(), base64.b64encode(value).decode())

def verify_password(password: str, encoded: str) -> bool:
    if not isinstance(encoded,str):
        return False
    try:
        kind, rounds, salt, expected = encoded.split('$')
        if kind != 'pbkdf2_sha256' or not 100_000 <= int(rounds) <= 2_000_000:
            return False
        actual = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), base64.b64decode(salt, validate=True), int(rounds))
        return hmac.compare_digest(actual, base64.b64decode(expected, validate=True))
    except (ValueError, TypeError):
        return False

# Equal-cost verification for an unknown account, without storing a real password.
DUMMY_HASH = hash_password(new_token())
