"""
core/database.py  (فاز ۴)

لایه‌ی خام ذخیره‌سازی -- طبق تصمیم فایل مرجع بخش۳ («ذخیره‌سازی: SQLite
(WAL mode) + JSON»). این ماژول هیچ دانشی از قواعد بازی (سکه/جواهر/
انرژی/...) نداره -- فقط یک key-value store مبتنی بر SQLite با
WAL mode، که مقدار هر کلید یک بلوب JSON دلخواه است. لایه‌ی بالاتر
(`game_logic/save_manager.py`) معنای هر کلید رو تعریف می‌کنه.

این تفکیک عمداً هم‌راستا با بقیه‌ی پروژه‌ست: دقیقاً همون اصلی که
`scene_builder.py` رو از `main.py` جدا نگه داشت (قابل‌تست‌بودن بدون
وابستگی سنگین)، اینجا هم `Database` رو از منطق بازی جدا نگه می‌داره.

چرا key-value-of-JSON به‌جای schema رابطه‌ای کامل: فایل مرجع می‌گه
«SQLite + JSON» رو در کنار هم، نه یک schema رابطه‌ای مفصل؛ و چون
پروژه هنوز فاز به فاز در حال تغییره (فیلدهای EconomyManager/
BattlePassManager و... قطعاً در فازهای بعدی عوض/اضافه می‌شن)، یک
schema سفت‌وسخت رابطه‌ای یعنی migration مکرر. یک ستون value از نوع
TEXT (JSON) این مشکل رو کاملاً کنار می‌زنه، بدون از دست دادن
تراکنشی‌بودن و ایمنی SQLite.
"""
import json
import os
import sqlite3
import time

DEFAULT_DB_PATH = os.path.join('data', 'save.db')


class Database:
    """پوشش نازک روی sqlite3 با WAL mode -- یک جدول key-value با
    مقدار JSON. ایمن دربرابر چندبار باز شدن هم‌زمان (WAL دقیقاً برای
    همین طراحی شده: خواننده‌ها بلاک نمی‌شن)."""

    def __init__(self, path=DEFAULT_DB_PATH):
        self.path = path
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        self._conn = sqlite3.connect(self.path)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS kv_store ("
            "  key TEXT PRIMARY KEY,"
            "  value TEXT NOT NULL,"
            "  updated_at REAL NOT NULL"
            ")"
        )
        self._conn.commit()

    def get(self, key, default=None):
        row = self._conn.execute(
            "SELECT value FROM kv_store WHERE key = ?", (key,)
        ).fetchone()
        if row is None:
            return default
        return json.loads(row[0])

    def set(self, key, value):
        payload = json.dumps(value, ensure_ascii=False)
        self._conn.execute(
            "INSERT INTO kv_store (key, value, updated_at) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value, "
            "updated_at = excluded.updated_at",
            (key, payload, time.time()),
        )
        self._conn.commit()

    def delete(self, key):
        self._conn.execute("DELETE FROM kv_store WHERE key = ?", (key,))
        self._conn.commit()

    def keys(self):
        rows = self._conn.execute("SELECT key FROM kv_store").fetchall()
        return [r[0] for r in rows]

    def close(self):
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
