import time
from src.videotranslation.client import StatusCache

def test_cache_set_and_get():
    cache = StatusCache()
    cache.set(key="abcd",value=4)
    assert cache.get("abcd") == 4

def test_cache_not_exists_get():
    cache = StatusCache()
    assert cache.get("abcd") == None

def test_cache_not_stale_entry():
    cache = StatusCache(ttl_seconds=40)
    cache.set(key="abcd",value=4)
    time.sleep(70)
    assert cache.get("abcd") == None