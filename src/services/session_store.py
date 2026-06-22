# Simple in-memory session store — replaces Redis.
# State is lost when the process restarts (acceptable for dev/capstone).
_store: dict = {}


def set_val(session_id: str, key: str, value):
    _store.setdefault(session_id, {})[key] = value


def get_val(session_id: str, key: str, default=None):
    return _store.get(session_id, {}).get(key, default)


def get_session(session_id: str) -> dict:
    return dict(_store.get(session_id, {}))
