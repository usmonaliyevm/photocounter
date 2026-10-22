"""SQLite baza: agentlar, guruhlar, foto otchyotlar, takrorlar va sozlamalar."""
from typing import List, Optional, Tuple

import aiosqlite

from config import DB_PATH, DEFAULT_WEEKLY_PLAN

SCHEMA = """
CREATE TABLE IF NOT EXISTS agents (
    user_id     INTEGER PRIMARY KEY,
    full_name   TEXT NOT NULL,
    username    TEXT,
    weekly_plan INTEGER,
    active      INTEGER NOT NULL DEFAULT 1,
    display_name TEXT
);
CREATE TABLE IF NOT EXISTS chats (
    chat_id  INTEGER PRIMARY KEY,
    title    TEXT NOT NULL DEFAULT '',
    owner_id INTEGER
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
    phash          TEXT,
    rejected       INTEGER NOT NULL DEFAULT 0,
    rejected_by    INTEGER,
    UNIQUE (chat_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_reports_chat_day ON reports (chat_id, day);
CREATE INDEX IF NOT EXISTS idx_reports_file ON reports (chat_id, file_unique_id);
CREATE TABLE IF NOT EXISTS duplicates (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id     INTEGER NOT NULL,
    message_id  INTEGER NOT NULL,
    user_id     INTEGER NOT NULL,
    original_id INTEGER NOT NULL,
    distance    INTEGER NOT NULL,
    day         TEXT NOT NULL,
    UNIQUE (chat_id, message_id)
);
CREATE INDEX IF NOT EXISTS idx_dups_chat_day ON duplicates (chat_id, day);
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
        await self._migrate()
        await self._conn.commit()

    async def _migrate(self) -> None:
        """Eski bazaga yangi ustunlarni qo'shish."""
        cur = await self.conn.execute("PRAGMA table_info(reports)")
        cols = {row["name"] for row in await cur.fetchall()}
        if "phash" not in cols:
            await self.conn.execute("ALTER TABLE reports ADD COLUMN phash TEXT")
        if "rejected" not in cols:
            await self.conn.execute("ALTER TABLE reports ADD COLUMN rejected INTEGER NOT NULL DEFAULT 0")
            await self.conn.execute("ALTER TABLE reports ADD COLUMN rejected_by INTEGER")
        cur = await self.conn.execute("PRAGMA table_info(agents)")
        cols = {row["name"] for row in await cur.fetchall()}
        if "display_name" not in cols:
            await self.conn.execute("ALTER TABLE agents ADD COLUMN display_name TEXT")
        cur = await self.conn.execute("PRAGMA table_info(chats)")
        cols = {row["name"] for row in await cur.fetchall()}
        if "owner_id" not in cols:
            await self.conn.execute("ALTER TABLE chats ADD COLUMN owner_id INTEGER")

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

    async def find_agent_by_username(self, username: str) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM agents WHERE lower(username) = lower(?)", (username.lstrip("@"),)
        )
        return await cur.fetchone()

    async def set_display_name(self, user_id: int, name: Optional[str]) -> None:
        """Admin bergan ism (+ism). None bo'lsa Telegram ismi ishlatiladi."""
        await self.conn.execute("UPDATE agents SET display_name = ? WHERE user_id = ?", (name, user_id))
        await self.conn.commit()

    async def name_of(self, user_id: int, fallback: str) -> str:
        """Hisobotlarda ko'rinadigan ism: berilgan ism, bo'lmasa Telegram ismi."""
        row = await self.get_agent(user_id)
        if row is None:
            return fallback
        return row["display_name"] or row["full_name"] or fallback

    async def set_agent_active(self, user_id: int, active: bool) -> None:
        await self.conn.execute("UPDATE agents SET active = ? WHERE user_id = ?", (1 if active else 0, user_id))
        await self.conn.commit()

    async def list_agents_with_plan(self) -> List[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT user_id, username, weekly_plan, COALESCE(display_name, full_name) AS full_name "
            "FROM agents WHERE weekly_plan IS NOT NULL AND active = 1 ORDER BY full_name"
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

    async def get_chat(self, chat_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM chats WHERE chat_id = ?", (chat_id,))
        return await cur.fetchone()

    async def set_chat_owner(self, chat_id: int, owner_id: int) -> None:
        """Botni guruhga qo'shgan odam: hisobotlar unga boradi."""
        await self.conn.execute("UPDATE chats SET owner_id = ? WHERE chat_id = ?", (owner_id, chat_id))
        await self.conn.commit()

    async def remove_chat(self, chat_id: int) -> None:
        await self.conn.execute("DELETE FROM chats WHERE chat_id = ?", (chat_id,))
        await self.conn.commit()

    async def list_chats(self) -> List[aiosqlite.Row]:
        cur = await self.conn.execute("SELECT * FROM chats")
        return await cur.fetchall()

    # ---------- sozlamalar ----------
    async def get_setting(self, key: str) -> Optional[str]:
        cur = await self.conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row["value"] if row else None

    async def set_setting(self, key: str, value: str) -> None:
        await self.conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await self.conn.commit()

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
    _REPORT_WITH_NAME = (
        "SELECT r.*, COALESCE(a.display_name, a.full_name) AS full_name, a.username "
        "FROM reports r LEFT JOIN agents a ON a.user_id = r.user_id "
    )

    async def is_known_message(self, chat_id: int, message_id: int) -> bool:
        """Bu xabar avval sanalgan yoki takror deb belgilanganmi (import uchun)."""
        cur = await self.conn.execute(
            "SELECT 1 FROM reports WHERE chat_id = ? AND message_id = ? "
            "UNION ALL SELECT 1 FROM duplicates WHERE chat_id = ? AND message_id = ? LIMIT 1",
            (chat_id, message_id, chat_id, message_id),
        )
        return await cur.fetchone() is not None

    async def get_report(self, chat_id: int, message_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(
            self._REPORT_WITH_NAME + "WHERE r.chat_id = ? AND r.message_id = ?", (chat_id, message_id)
        )
        return await cur.fetchone()

    async def set_rejected(
        self, chat_id: int, message_id: int, rejected: bool, by_user_id: Optional[int]
    ) -> Optional[aiosqlite.Row]:
        """Rasmni soxta deb belgilash (/fake) yoki qaytarish (/unfake). Hisobda bo'lmasa None."""
        row = await self.get_report(chat_id, message_id)
        if row is None:
            return None
        await self.conn.execute(
            "UPDATE reports SET rejected = ?, rejected_by = ? WHERE id = ?",
            (1 if rejected else 0, by_user_id if rejected else None, int(row["id"])),
        )
        await self.conn.commit()
        return row

    async def find_by_file(self, chat_id: int, file_unique_id: str) -> Optional[aiosqlite.Row]:
        """Aynan shu Telegram fayli (forward / qayta yuborish) avval sanalganmi."""
        cur = await self.conn.execute(
            self._REPORT_WITH_NAME + "WHERE r.chat_id = ? AND r.file_unique_id = ? LIMIT 1",
            (chat_id, file_unique_id),
        )
        return await cur.fetchone()

    async def find_similar(
        self, chat_id: int, phash: str, threshold: int, since_day: str
    ) -> Optional[Tuple[aiosqlite.Row, int]]:
        """Mazmunan bir xil rasm (qayta yuklangan nusxa) bormi: eng yaqinini qaytaradi."""
        cur = await self.conn.execute(
            self._REPORT_WITH_NAME + "WHERE r.chat_id = ? AND r.day >= ? AND r.phash IS NOT NULL",
            (chat_id, since_day),
        )
        h = int(phash, 16)
        best: Optional[Tuple[aiosqlite.Row, int]] = None
        async for row in cur:
            d = bin(h ^ int(row["phash"], 16)).count("1")
            if d <= threshold and (best is None or d < best[1]):
                best = (row, d)
        return best

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
        phash: Optional[str],
    ) -> bool:
        """True — sanaldi; False — bu xabar avval qayd etilgan."""
        cur = await self.conn.execute(
            "INSERT OR IGNORE INTO reports "
            "(chat_id, message_id, user_id, file_unique_id, media_group_id, sent_at, day, phash) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (chat_id, message_id, user_id, file_unique_id, media_group_id, sent_at, day, phash),
        )
        await self.conn.commit()
        return bool(cur.rowcount)

    async def add_duplicate(
        self, *, chat_id: int, message_id: int, user_id: int, original_id: int, distance: int, day: str
    ) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO duplicates (chat_id, message_id, user_id, original_id, distance, day) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (chat_id, message_id, user_id, original_id, distance, day),
        )
        await self.conn.commit()

    async def counts_by_agent(self, chat_id: int, day_from: str, day_to: str) -> List[aiosqlite.Row]:
        """Shu guruhda qachondir rasm yuborgan faol agentlar: davr ichidagi soni va takrorlari (0 bo'lsa ham)."""
        cur = await self.conn.execute(
            """
            SELECT a.user_id, COALESCE(a.display_name, a.full_name) AS full_name, a.username, a.weekly_plan,
                   COALESCE(r.cnt, 0) AS cnt, COALESCE(d.dups, 0) AS dups, COALESCE(f.fakes, 0) AS fakes
            FROM agents a
            JOIN (
                SELECT user_id FROM reports WHERE chat_id = ?
                UNION
                SELECT user_id FROM duplicates WHERE chat_id = ?
            ) c ON c.user_id = a.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS cnt FROM reports
                WHERE chat_id = ? AND day BETWEEN ? AND ? AND rejected = 0
                GROUP BY user_id
            ) r ON r.user_id = a.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS fakes FROM reports
                WHERE chat_id = ? AND day BETWEEN ? AND ? AND rejected = 1
                GROUP BY user_id
            ) f ON f.user_id = a.user_id
            LEFT JOIN (
                SELECT user_id, COUNT(*) AS dups FROM duplicates
                WHERE chat_id = ? AND day BETWEEN ? AND ?
                GROUP BY user_id
            ) d ON d.user_id = a.user_id
            WHERE a.active = 1
            ORDER BY cnt DESC, full_name
            """,
            (chat_id, chat_id, chat_id, day_from, day_to, chat_id, day_from, day_to, chat_id, day_from, day_to),
        )
        return await cur.fetchall()

    async def count_for_user(
        self, user_id: int, day_from: str, day_to: str, chat_id: Optional[int] = None
    ) -> int:
        sql = "SELECT COUNT(*) AS n FROM reports WHERE user_id = ? AND day BETWEEN ? AND ? AND rejected = 0"
        params = [user_id, day_from, day_to]
        if chat_id is not None:
            sql += " AND chat_id = ?"
            params.append(chat_id)
        cur = await self.conn.execute(sql, params)
        row = await cur.fetchone()
        return int(row["n"]) if row else 0


db = Database(DB_PATH)
