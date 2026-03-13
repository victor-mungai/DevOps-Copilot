from datetime import datetime
from threading import Lock
from typing import Optional

credential_store = {}
store_lock = Lock()


def get_cached_credentials(tenant_id: str) -> Optional[dict]:
    with store_lock:
        creds = credential_store.get(tenant_id)
        if not creds:
            return None
        if creds["expiration"] <= datetime.utcnow():
            return None
        return creds


def store_credentials(tenant_id: str, creds: dict) -> None:
    with store_lock:
        credential_store[tenant_id] = {
            "access_key": creds["AccessKeyId"],
            "secret_key": creds["SecretAccessKey"],
            "session_token": creds["SessionToken"],
            "expiration": creds["Expiration"],
        }
