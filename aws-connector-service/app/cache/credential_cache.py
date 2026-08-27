from datetime import datetime, timezone
from threading import Lock
from typing import Optional

credential_store = {}
store_lock = Lock()


def _key(tenant_id: str, account_id: str | None = None) -> str:
    return f"{tenant_id}:{account_id or ''}"


def get_cached_credentials(tenant_id: str, account_id: str | None = None) -> Optional[dict]:
    with store_lock:
        creds = credential_store.get(_key(tenant_id, account_id))
        if not creds:
            return None
        if creds["expiration"] <= datetime.now(timezone.utc):
            return None
        return creds


def store_credentials(tenant_id: str, creds: dict, account_id: str | None = None) -> None:
    with store_lock:
        credential_store[_key(tenant_id, account_id)] = {
            "access_key": creds["AccessKeyId"],
            "secret_key": creds["SecretAccessKey"],
            "session_token": creds["SessionToken"],
            "expiration": creds["Expiration"],
            "assumed_account_id": creds.get("AssumedAccountId"),
            "assumed_arn": creds.get("AssumedArn"),
        }
