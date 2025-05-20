import os
import sqlite3
import time
from typing import Any, Optional


class BaseCache:
    def set(self, key: str, value: Any, **kwargs):
        raise NotImplementedError

    def get(self, key: str) -> Optional[Any]:
        raise NotImplementedError

    def delete(self, key: str):
        raise NotImplementedError

    def clear(self):
        raise NotImplementedError


class SQLiteCache(BaseCache):
    def __init__(self, db_file: str, seed: int, default_ttl: int = 3600):
        """
        Initializes the SQLite cache.

        :param db_file: Path to the SQLite database file.
        :param seed: The integer seed to group related keys.
        :param default_ttl: Default time-to-live (TTL) for cache entries in seconds.
        """
        self.db_file = db_file
        self.seed = seed
        self.default_ttl = default_ttl
        if not os.path.exists(self.db_file):
            print(f"Creating new SQLite database at {self.db_file}.")
        self._initialize_db()

    def _initialize_db(self):
        """Creates the cache table if it doesn't exist."""
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                sql = """
                CREATE TABLE IF NOT EXISTS cache (
                    seed INTEGER,
                    key TEXT,
                    value TEXT,
                    expires_at REAL,
                    PRIMARY KEY (seed, key)
                )
                """
                print("Executing SQL:", sql)
                cursor.execute(sql)
                conn.commit()
        except sqlite3.DatabaseError as e:
            print("Database initialization error:", e)
            raise

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Sets a value in the cache with an optional TTL.

        :param key: The key to store the value under.
        :param value: The value to cache.
        :param ttl: Time-to-live in seconds. Defaults to the cache's default TTL.
        """
        ttl = ttl or self.default_ttl
        expiration_time = time.time() + ttl
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO cache (seed, key, value, expires_at)
                    VALUES (?, ?, ?, ?)
                """, (self.seed, key, str(value), expiration_time))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print("Database set error:", e)
            raise

    def get(self, key: str) -> Optional[Any]:
        """
        Retrieves a value from the cache.

        :param key: The key to look up.
        :return: The cached value, or None if the key does not exist or is expired.
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT value, expires_at FROM cache WHERE seed = ? AND key = ?
                """, (self.seed, key))
                row = cursor.fetchone()

                if row:
                    value, expires_at = row
                    if time.time() < expires_at:
                        return value
                    else:
                        self.delete(key)  # Remove expired entry
        except sqlite3.DatabaseError as e:
            print("Database get error:", e)
            raise
        return None

    def delete(self, key: str):
        """
        Deletes a key from the cache.

        :param key: The key to delete.
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM cache WHERE seed = ? AND key = ?
                """, (self.seed, key))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print("Database delete error:", e)
            raise

    def clear(self):
        """
        Clears all cache entries for the current seed.
        """
        try:
            with sqlite3.connect(self.db_file) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    DELETE FROM cache WHERE seed = ?
                """, (self.seed,))
                conn.commit()
        except sqlite3.DatabaseError as e:
            print("Database clear error:", e)
            raise

# Example usage
# if __name__ == "__main__":
#     cache = SQLiteCache("cache.db", default_ttl=600)
#
#     # Set a value in the cache
#     cache.set("example_key", "example_value", ttl=300)
#
#     # Retrieve the value
#     value = cache.get("example_key")
#     print("Retrieved value:", value
