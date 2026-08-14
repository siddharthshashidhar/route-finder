import json
import hashlib
import os
import time

CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)


def _cache_key(lat, lon, radius_km, n_bearings, mode="loop"):
    raw = f"{lat}_{lon}_{radius_km}_{n_bearings}_{mode}"
    return hashlib.md5(raw.encode()).hexdigest()


def load_cached_candidates(lat, lon, radius_km, n_bearings, mode="loop"):
    key = _cache_key(lat, lon, radius_km, n_bearings, mode)
    path = os.path.join(CACHE_DIR, f"{key}.json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    return None


def save_candidates(lat, lon, radius_km, n_bearings, candidates, mode="loop"):
    key = _cache_key(lat, lon, radius_km, n_bearings, mode)
    path = os.path.join(CACHE_DIR, f"{key}.json")
    with open(path, "w") as f:
        json.dump(candidates, f)

import datetime

def _usage_key():
    today = datetime.date.today().isoformat()
    return os.path.join(CACHE_DIR, f"usage_{today}.json")


def get_usage_count():
    path = _usage_key()
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f).get("count", 0)
    return 0


def increment_usage(n=1):
    path = _usage_key()
    count = get_usage_count() + n
    with open(path, "w") as f:
        json.dump({"count": count}, f)
    return count