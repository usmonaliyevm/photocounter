"""SQLite baza: agentlar, guruhlar, foto otchyotlar va sozlamalar."""
from typing import List, Optional

import aiosqlite

from config import DB_PATH, DEFAULT_WEEKLY_PLAN

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    user_id     INTEGER PRIMARY KEY,
    full_name   TEXT NOT NULL,
    username    TEXT,
    weekly_plan INTEGER,
    active      INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS chats (
    chat_id INTEGER PRIMARY KEY,
    title   TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS reports (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id        INTEGER NOT NULL,
    message_id     INTEGER NOT NULL,
    user_id        INTEGER NOT NULL,
    file_unique_id TEXT NOT NULL,
    media_group_id TEXT,
    sent_at        TEXT NOT NULL,
    day            TEXT NOT NULL,
    UNIQUE (chat_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_reports_chat_day ON reports (chat_id, day);
CREATE INDEX IF NOT EXISTS idx_reports_file ON reports (chat_id, file_unique_id);
CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
"""


class Database:
    def __init__(self, path: str) -> None:
        self.path = path
        self._conn: Optional[aiosqlite.Connection] = None

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database.connect() chaqirilmagan")
        return self._conn

    async def connect(self) -> None:
        self._conn = await aiosqlite.connect(self.path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(SCHEMA)
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn is not None:
            await self._conn.close()
            self._conn = None

    # ---------- agentlar ----------
    async def upsert_agent(self, user_id: int, full_name: str, username: Optional[str]) -> None:
        await self.conn.execute(
            "INSERT INTO agents (user_id, full_name, username) VALUES (?, ?, ?) "
            "ON CONFLICT(user_id) DO UPDATE SET full_name = excluded.full_name, username = excluded.username",
            (user_id, full_name, username),
        )
        await self.conn.commit()

    async def get_agent(self, user_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM agents WHERE user_id = ?", (user_id,))
        return await cur.fetchone()

    async def set_agent_plan(self, user_id: int, plan: Optional[int]) -> None:
        await self.conn.execute("UPDATE agents SET weekly_plan = ? WHERE user_id = ?", (plan, user_id))
        await self.conn.commit()

    async def set_agent_active(self, user_id: int, active: bool) -> None:
        await self.conn.execute("UPDATE agents SET active = ? WHERE user_id = ?", (1 if active else 0, user_id))
        await self.conn.commit()

    async def list_agents_with_plan(self) -> List[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM agents WHERE weekly_plan IS NOT NULL AND active = 1 ORDER BY full_name"
        )
        return await cur.fetchall()

    # ---------- guruhlar ----------
    async def upsert_chat(self, chat_id: int, title: str) -> None:
        await self.conn.execute(
            "INSERT INTO chats (chat_id, title) VALUES (?, ?) "
            "ON CONFLICT(chat_id) DO UPDATE SET title = excluded.title",
            (chat_id, title),
        )
        await self.conn.commit()

    async def remove_chat(self, chat_id: int) -> None:
        await self.conn.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
        await self.conn.commit()

    async def list_chats(self) -> List[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM chats")
        return await cur.fetchall()

    # ---------- sozlamalar ----------
    async def get_default_plan(self) -> int:
        cur = await self.conn.execute("SELECT value FROM settings WHERE key = 'weekly_plan'")
        row = await cur.fetchone()
        return int(row["value"]) if row else DEFAULT_WEEKLY_PLAN

    async def set_default_plan(self, plan: int) -> None:
        await self.conn.execute(
            "INSERT INTO settings (key, value) VALUES ('weekly_plan', ?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (str(plan),),
        )
        await self.conn.commit()

    # ---------- foto otchyotlar ----------
    async def add_report(
        self,
        *,
        chat_id: int,
        message_id: int,
        user_id: int,
        file_unique_id: str,
        media_group_id: Optional[str],
        sent_at: str,
        day: str,
    ) -> str:
        """Natija: 'ok' (sanaldi), 'duplicate' (shu rasm avval yuborilgan), 'exists' (shu xabar avval qayd etilgan)."""
        cur = await self.conn.execute(
            "SELECT 1 FROM reports WHERE chat_id = ? AND file_unique_id = ?", (chat_id, file_unique_id)
        )
        if await cur.fetchone():
            return "duplicate"
        cur = await self.conn.execute(
            "INSERT OR IGNORE INTO reports (chat_id, message_id, user_id, file_unique_id, media_group_id, sent_at, day) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (chat_id, message_id, user_id, file_unique_id, media_group_id, sent_at, day),
        )
        await self.conn.commit()
        return "ok" if cur.rowcount else "exists"

    async def counts_by_agent(self, chat_id: int, day_from: str, day_to: str) -> List[aiosqlite.Row]:
        """Shu guruhda qachondir otchyot yuborgan faol agentlar, davr ichidagi soni bilan (0 bo'lsa ham)."""
        cur = await self.conn.execute(
            """
            SELECT a.user_id, a.full_name, a.username, a.weekly_plan, COALESCE(r.cnt, 0) AS cnt
            FROM agents a
            JOIN (SELECT DISTINCT user_id FROM reports WHERE chat_id = ?) c ON c.user_id = a.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS cnt FROM reports
                WHERE chat_id = ? AND day BETWEEN ? AND ?
                GROUP BY user_id
            ) r ON r.user_id = a.user_id
            WHERE a.active = 1
            ORDER BY cnt DESC, a.full_name
            """,
            (chat_id, chat_id, day_from, day_to),
        )
        return await cur.fetchall()

    async def count_for_user(
        self, user_id: int, day_from: str, day_to: str, chat_id: Optional[int] = None
    ) -> int:
        sql = "SELECT COUNT(*) AS n FROM reports WHERE user_id = ? AND day BETWEEN ? AND ?"
        params = [user_id, day_from, day_to]
        if chat_id is not None:
            sql += " AND chat_id = ?"
            params.append(chat_id)
        cur = await self.conn.execute(sql, params)
        row = await cur.fetchone()
        return int(row["n"]) if row else 0


db = Database(DB_PATH)
