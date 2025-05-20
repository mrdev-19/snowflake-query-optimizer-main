import pytest
import sqlite3
import time
from unittest.mock import patch, Mock
import os
from snowflake_optimizer.cache import SQLiteCache, BaseCache


@pytest.fixture
def temp_db(tmp_path):
    db_file = tmp_path / "test_cache.db"
    return str(db_file)


@pytest.fixture
def cache(temp_db):
    return SQLiteCache(temp_db, seed=1, default_ttl=60)


def test_base_cache_abstract_methods():
    base_cache = BaseCache()
    with pytest.raises(NotImplementedError):
        base_cache.set("key", "value")
    with pytest.raises(NotImplementedError):
        base_cache.get("key")
    with pytest.raises(NotImplementedError):
        base_cache.delete("key")
    with pytest.raises(NotImplementedError):
        base_cache.clear()


def test_sqlite_cache_initialization(temp_db):
    cache = SQLiteCache(temp_db, seed=1)
    assert cache.db_file == temp_db
    assert cache.seed == 1
    assert cache.default_ttl == 3600

    # Verify table creation
    with sqlite3.connect(temp_db) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='cache'")
        assert cursor.fetchone() is not None


def test_sqlite_cache_set_get(cache):
    cache.set("test_key", "test_value")
    assert cache.get("test_key") == "test_value"


def test_sqlite_cache_ttl(cache):
    # Set with short TTL
    cache.set("test_key", "test_value", ttl=1)
    assert cache.get("test_key") == "test_value"

    # Wait for expiration
    time.sleep(1.1)
    assert cache.get("test_key") is None


def test_sqlite_cache_delete(cache):
    cache.set("test_key", "test_value")
    cache.delete("test_key")
    assert cache.get("test_key") is None


def test_sqlite_cache_clear(cache):
    cache.set("key1", "value1")
    cache.set("key2", "value2")
    cache.clear()
    assert cache.get("key1") is None
    assert cache.get("key2") is None


def test_sqlite_cache_different_seeds(temp_db):
    cache1 = SQLiteCache(temp_db, seed=1)
    cache2 = SQLiteCache(temp_db, seed=2)

    cache1.set("key", "value1")
    cache2.set("key", "value2")

    assert cache1.get("key") == "value1"
    assert cache2.get("key") == "value2"


def test_sqlite_cache_db_error_handling(temp_db):
    cache = SQLiteCache(temp_db, seed=1)

    with patch('sqlite3.connect') as mock_connect:
        mock_connect.side_effect = sqlite3.DatabaseError("Test error")

        with pytest.raises(sqlite3.DatabaseError):
            cache.set("key", "value")

        with pytest.raises(sqlite3.DatabaseError):
            cache.get("key")

        with pytest.raises(sqlite3.DatabaseError):
            cache.delete("key")

        with pytest.raises(sqlite3.DatabaseError):
            cache.clear()


def test_sqlite_cache_non_string_values(cache):
    test_values = [
        42,
        3.14,
        ["list", "of", "items"],
        {"key": "value"},
        True,
        None
    ]

    for value in test_values:
        cache.set("test_key", value)
        retrieved = cache.get("test_key")
        assert str(value) == retrieved


def test_sqlite_cache_overwrite(cache):
    cache.set("test_key", "original_value")
    cache.set("test_key", "new_value")
    assert cache.get("test_key") == "new_value"


def test_sqlite_cache_expired_cleanup(cache):
    cache.set("test_key", "test_value", ttl=1)
    time.sleep(1.1)

    # Trigger cleanup by accessing the key
    assert cache.get("test_key") is None

    # Verify key was removed from database
    with sqlite3.connect(cache.db_file) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM cache WHERE key = ?", ("test_key",))
        count = cursor.fetchone()[0]
        assert count == 0