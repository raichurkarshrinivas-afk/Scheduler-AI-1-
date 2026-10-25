import base64
import hashlib
import hmac
import json
import time
from typing import Any, Dict, Optional
from cryptography.fernet import Fernet
from app.core.config import settings


def _get_fernet_key() -> bytes:
    if settings.GOOGLE_ENCRYPTION_KEY:
        try:
            raw = settings.GOOGLE_ENCRYPTION_KEY.encode('utf-8')
            # Check if valid base64 32-byte
            decoded = base64.urlsafe_b64decode(raw)
            if len(decoded) == 32:
                return raw
        except Exception:
            pass
    # Deterministically derive 32 bytes from SECRET_KEY
    digest = hashlib.sha256(settings.SECRET_KEY.encode('utf-8')).digest()
    return base64.urlsafe_b64encode(digest)


def encrypt_token(plain_text: str) -> str:
    if not plain_text:
        return ''
    fernet = Fernet(_get_fernet_key())
    return fernet.encrypt(plain_text.encode('utf-8')).decode('utf-8')


def decrypt_token(cipher_text: str) -> str:
    if not cipher_text:
        return ''
    fernet = Fernet(_get_fernet_key())
    return fernet.decrypt(cipher_text.encode('utf-8')).decode('utf-8')


def sign_oauth_state(payload: Dict[str, Any]) -> str:
    payload_copy = dict(payload)
    payload_copy['ts'] = int(time.time())
    raw_json = json.dumps(payload_copy, sort_keys=True).encode('utf-8')
    b64_payload = base64.urlsafe_b64encode(raw_json).decode('utf-8')
    signature = hmac.new(
        settings.SECRET_KEY.encode('utf-8'),
        b64_payload.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return f'{b64_payload}.{signature}'


def verify_oauth_state(state: str, max_age_seconds: int = 600) -> Optional[Dict[str, Any]]:
    try:
        parts = state.split('.')
        if len(parts) != 2:
            return None
        b64_payload, signature = parts
        expected_sig = hmac.new(
            settings.SECRET_KEY.encode('utf-8'),
            b64_payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_sig):
            return None
        raw_json = base64.urlsafe_b64decode(b64_payload.encode('utf-8'))
        payload = json.loads(raw_json.decode('utf-8'))
        if time.time() - payload.get('ts', 0) > max_age_seconds:
            return None
        return payload
    except Exception:
        return None
