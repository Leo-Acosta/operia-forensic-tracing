"""Bounded, per-process throttling. Shared gateway quotas remain a deployment task."""
from threading import Lock
from time import monotonic
from operia.core.config import settings
_lock = Lock()
_buckets = {}

def reset_limits():
    with _lock:
        _buckets.clear()

def admit(peer, authentication=False):
    now = monotonic()
    keys = [("request", peer, settings.http_requests_per_minute)]
    if authentication:
        keys.append(("authentication", peer, settings.http_auth_per_minute))
    with _lock:
        for key in list(_buckets):
            if now - _buckets[key][0] >= 60:
                del _buckets[key]
        if len(_buckets) + len(keys) > 4096:
            return False
        if any(_buckets.get((kind, peer), (now, 0))[1] >= limit for kind, peer, limit in keys):
            return False
        for kind, peer, limit in keys:
            since, count = _buckets.get((kind, peer), (now, 0))
            _buckets[kind, peer] = (since, count + 1)
        return True
