from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiosqlite


@dataclass
class Account:
    id: int
    name: str
    phone: str
    api_id: int
    api_hash: str
    session_name: str
    enabled: bool
    created_at: str


@dataclass
class Chat:
    id: int
    account_id: int
    chat_id: int
    title: str
    username: str | None
    chat_type: str
    enabled: bool
    interval_minutes: float
    last_posted_at: str | None


@dataclass
class AdMessage:
    id: int
    account_id: int | None
    from_chat_id: int
    message_id: int
    label: str
    created_at: str


class Database:
    def __init__(self, path: Path, default_interval_minutes: float = 15.0) -> None:
        self.path = path
        self.default_interval_minutes = default_interval_minutes
        self._conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON")
        await self._init_schema()
        await self._migrate_schema()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def _init_schema(self) -> None:
        await self.conn.executescript(
            f"""
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                phone TEXT NOT NULL UNIQUE,
                api_id INTEGER NOT NULL,
                api_hash TEXT NOT NULL,
                session_name TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS chats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                username TEXT,
                chat_type TEXT NOT NULL DEFAULT 'unknown',
                enabled INTEGER NOT NULL DEFAULT 1,
                interval_minutes REAL NOT NULL DEFAULT {self.default_interval_minutes},
                last_posted_at TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(account_id, chat_id),
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS ad_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                account_id INTEGER,
                from_chat_id INTEGER NOT NULL,
                message_id INTEGER NOT NULL,
                label TEXT NOT NULL DEFAULT 'Основное',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS post_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_row_id INTEGER NOT NULL,
                success INTEGER NOT NULL,
                detail TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (chat_row_id) REFERENCES chats(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS kv_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_chats_account ON chats(account_id);
            CREATE INDEX IF NOT EXISTS idx_chats_enabled ON chats(enabled);
            CREATE INDEX IF NOT EXISTS idx_post_log_created ON post_log(created_at);
            """
        )
        await self.conn.commit()

    async def _migrate_schema(self) -> None:
        cur = await self.conn.execute("PRAGMA table_info(chats)")
        columns = {row[1] for row in await cur.fetchall()}
        if "interval_hours" in columns and "interval_minutes" not in columns:
            await self.conn.execute(
                "ALTER TABLE chats ADD COLUMN interval_minutes REAL NOT NULL DEFAULT 15"
            )
            await self.conn.execute(
                "UPDATE chats SET interval_minutes = interval_hours * 60"
            )
            await self.conn.commit()

    # --- Settings ---

    async def get_setting(self, key: str, default: str | None = None) -> str | None:
        cur = await self.conn.execute(
            "SELECT value FROM kv_settings WHERE key = ?", (key,)
        )
        row = await cur.fetchone()
        return row["value"] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        await self.conn.execute(
            """
            INSERT INTO kv_settings (key, value) VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value = excluded.value
            """,
            (key, value),
        )
        await self.conn.commit()

    async def is_scheduler_running(self) -> bool:
        return (await self.get_setting("scheduler_running", "0")) == "1"

    async def set_scheduler_running(self, running: bool) -> None:
        await self.set_setting("scheduler_running", "1" if running else "0")

    # --- Accounts ---

    async def add_account(
        self,
        name: str,
        phone: str,
        api_id: int,
        api_hash: str,
        session_name: str,
    ) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO accounts (name, phone, api_id, api_hash, session_name)
            VALUES (?, ?, ?, ?, ?)
            """,
            (name, phone, api_id, api_hash, session_name),
        )
        await self.conn.commit()
        return cur.lastrowid or 0

    async def get_accounts(self, only_enabled: bool = False) -> list[Account]:
        query = "SELECT * FROM accounts"
        if only_enabled:
            query += " WHERE enabled = 1"
        query += " ORDER BY id"
        cur = await self.conn.execute(query)
        rows = await cur.fetchall()
        return [self._row_to_account(r) for r in rows]

    async def get_account(self, account_id: int) -> Account | None:
        cur = await self.conn.execute(
            "SELECT * FROM accounts WHERE id = ?", (account_id,)
        )
        row = await cur.fetchone()
        return self._row_to_account(row) if row else None

    async def get_account_by_phone(self, phone: str) -> Account | None:
        cur = await self.conn.execute(
            "SELECT * FROM accounts WHERE phone = ?", (phone,)
        )
        row = await cur.fetchone()
        return self._row_to_account(row) if row else None

    async def toggle_account(self, account_id: int, enabled: bool) -> None:
        await self.conn.execute(
            "UPDATE accounts SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, account_id),
        )
        await self.conn.commit()

    async def delete_account(self, account_id: int) -> None:
        await self.conn.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
        await self.conn.commit()

    def _row_to_account(self, row: aiosqlite.Row) -> Account:
        return Account(
            id=row["id"],
            name=row["name"],
            phone=row["phone"],
            api_id=row["api_id"],
            api_hash=row["api_hash"],
            session_name=row["session_name"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
        )

    # --- Chats ---

    async def upsert_chat(
        self,
        account_id: int,
        chat_id: int,
        title: str,
        username: str | None,
        chat_type: str,
        *,
        enabled: bool | None = None,
        interval_minutes: float | None = None,
    ) -> int:
        cur = await self.conn.execute(
            "SELECT id, enabled, interval_minutes FROM chats WHERE account_id = ? AND chat_id = ?",
            (account_id, chat_id),
        )
        existing = await cur.fetchone()
        if existing:
            new_enabled = (
                bool(existing["enabled"]) if enabled is None else enabled
            )
            new_interval = (
                float(existing["interval_minutes"])
                if interval_minutes is None
                else interval_minutes
            )
            await self.conn.execute(
                """
                UPDATE chats
                SET title = ?, username = ?, chat_type = ?, enabled = ?, interval_minutes = ?
                WHERE id = ?
                """,
                (
                    title,
                    username,
                    chat_type,
                    1 if new_enabled else 0,
                    new_interval,
                    existing["id"],
                ),
            )
            await self.conn.commit()
            return existing["id"]

        default_enabled = True if enabled is None else enabled
        cur = await self.conn.execute(
            """
            INSERT INTO chats (account_id, chat_id, title, username, chat_type, enabled, interval_minutes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                account_id,
                chat_id,
                title,
                username,
                chat_type,
                1 if default_enabled else 0,
                interval_minutes
                if interval_minutes is not None
                else self.default_interval_minutes,
            ),
        )
        await self.conn.commit()
        return cur.lastrowid or 0

    async def get_chats(
        self,
        account_id: int | None = None,
        only_enabled: bool = False,
    ) -> list[Chat]:
        query = "SELECT * FROM chats WHERE 1=1"
        params: list[Any] = []
        if account_id is not None:
            query += " AND account_id = ?"
            params.append(account_id)
        if only_enabled:
            query += " AND enabled = 1"
        query += " ORDER BY account_id, title COLLATE NOCASE"
        cur = await self.conn.execute(query, params)
        rows = await cur.fetchall()
        return [self._row_to_chat(r) for r in rows]

    async def get_chat(self, chat_row_id: int) -> Chat | None:
        cur = await self.conn.execute("SELECT * FROM chats WHERE id = ?", (chat_row_id,))
        row = await cur.fetchone()
        return self._row_to_chat(row) if row else None

    async def toggle_chat(self, chat_row_id: int, enabled: bool) -> None:
        await self.conn.execute(
            "UPDATE chats SET enabled = ? WHERE id = ?",
            (1 if enabled else 0, chat_row_id),
        )
        await self.conn.commit()

    async def set_all_chats_enabled(self, enabled: bool, account_id: int | None = None) -> int:
        if account_id is None:
            cur = await self.conn.execute(
                "UPDATE chats SET enabled = ?", (1 if enabled else 0,)
            )
        else:
            cur = await self.conn.execute(
                "UPDATE chats SET enabled = ? WHERE account_id = ?",
                (1 if enabled else 0, account_id),
            )
        await self.conn.commit()
        return cur.rowcount

    async def set_chat_interval(self, chat_row_id: int, minutes: float) -> None:
        await self.conn.execute(
            "UPDATE chats SET interval_minutes = ? WHERE id = ?",
            (minutes, chat_row_id),
        )
        await self.conn.commit()

    async def set_default_interval_all(self, minutes: float, account_id: int | None = None) -> int:
        if account_id is None:
            cur = await self.conn.execute(
                "UPDATE chats SET interval_minutes = ?", (minutes,)
            )
        else:
            cur = await self.conn.execute(
                "UPDATE chats SET interval_minutes = ? WHERE account_id = ?",
                (minutes, account_id),
            )
        await self.conn.commit()
        return cur.rowcount

    async def update_last_posted(self, chat_row_id: int, when: datetime | None = None) -> None:
        ts = (when or datetime.utcnow()).isoformat()
        await self.conn.execute(
            "UPDATE chats SET last_posted_at = ? WHERE id = ?",
            (ts, chat_row_id),
        )
        await self.conn.commit()

    async def delete_chat(self, chat_row_id: int) -> None:
        await self.conn.execute("DELETE FROM chats WHERE id = ?", (chat_row_id,))
        await self.conn.commit()

    async def count_enabled_chats(self) -> int:
        cur = await self.conn.execute("SELECT COUNT(*) AS c FROM chats WHERE enabled = 1")
        row = await cur.fetchone()
        return int(row["c"]) if row else 0

    def _row_to_chat(self, row: aiosqlite.Row) -> Chat:
        minutes = row["interval_minutes"]
        if minutes is None and "interval_hours" in row.keys():
            minutes = float(row["interval_hours"]) * 60
        return Chat(
            id=row["id"],
            account_id=row["account_id"],
            chat_id=row["chat_id"],
            title=row["title"],
            username=row["username"],
            chat_type=row["chat_type"],
            enabled=bool(row["enabled"]),
            interval_minutes=float(minutes or self.default_interval_minutes),
            last_posted_at=row["last_posted_at"],
        )

    # --- Messages ---

    async def set_ad_message(
        self,
        from_chat_id: int,
        message_id: int,
        account_id: int | None = None,
        label: str = "Основное",
    ) -> int:
        if account_id is None:
            await self.conn.execute("DELETE FROM ad_messages WHERE account_id IS NULL")
        else:
            await self.conn.execute(
                "DELETE FROM ad_messages WHERE account_id = ?", (account_id,)
            )
        cur = await self.conn.execute(
            """
            INSERT INTO ad_messages (account_id, from_chat_id, message_id, label)
            VALUES (?, ?, ?, ?)
            """,
            (account_id, from_chat_id, message_id, label),
        )
        await self.conn.commit()
        return cur.lastrowid or 0

    async def get_ad_message(self, account_id: int) -> AdMessage | None:
        cur = await self.conn.execute(
            "SELECT * FROM ad_messages WHERE account_id = ? ORDER BY id DESC LIMIT 1",
            (account_id,),
        )
        row = await cur.fetchone()
        if row:
            return self._row_to_message(row)
        cur = await self.conn.execute(
            "SELECT * FROM ad_messages WHERE account_id IS NULL ORDER BY id DESC LIMIT 1"
        )
        row = await cur.fetchone()
        return self._row_to_message(row) if row else None

    async def has_ad_message(self) -> bool:
        cur = await self.conn.execute("SELECT COUNT(*) AS c FROM ad_messages")
        row = await cur.fetchone()
        return bool(row and row["c"])

    async def list_ad_messages(self) -> list[AdMessage]:
        cur = await self.conn.execute(
            "SELECT * FROM ad_messages ORDER BY account_id IS NOT NULL, account_id, id DESC"
        )
        rows = await cur.fetchall()
        return [self._row_to_message(r) for r in rows]

    def _row_to_message(self, row: aiosqlite.Row) -> AdMessage:
        return AdMessage(
            id=row["id"],
            account_id=row["account_id"],
            from_chat_id=row["from_chat_id"],
            message_id=row["message_id"],
            label=row["label"],
            created_at=row["created_at"],
        )

    # --- Post log ---

    async def log_post(self, chat_row_id: int, success: bool, detail: str = "") -> None:
        await self.conn.execute(
            "INSERT INTO post_log (chat_row_id, success, detail) VALUES (?, ?, ?)",
            (chat_row_id, 1 if success else 0, detail[:500]),
        )
        await self.conn.commit()
        await self.conn.execute(
            """
            DELETE FROM post_log WHERE id NOT IN (
                SELECT id FROM post_log ORDER BY id DESC LIMIT 500
            )
            """
        )
        await self.conn.commit()

    async def recent_post_log(self, limit: int = 10) -> list[str]:
        cur = await self.conn.execute(
            """
            SELECT p.detail, p.success, p.created_at, c.title
            FROM post_log p
            JOIN chats c ON c.id = p.chat_row_id
            ORDER BY p.id DESC
            LIMIT ?
            """,
            (limit,),
        )
        rows = await cur.fetchall()
        lines = []
        for row in rows:
            mark = "✅" if row["success"] else "❌"
            lines.append(f"{mark} {row['created_at'][:19]} {row['title']}: {row['detail']}")
        return lines
