"""SQLite helpers for FamilyDaily."""

import os
from pathlib import Path

import aiosqlite

DATA_DIR = Path(os.environ.get("FAMILYDAILY_DATA", "/data"))
DB_PATH = DATA_DIR / "familydaily.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS person (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    color TEXT NOT NULL DEFAULT '#4a90d9',
    emoji TEXT,
    calendar_entity_id TEXT
);
CREATE TABLE IF NOT EXISTS shopping_list (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    icon TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS shopping_item (
    id INTEGER PRIMARY KEY,
    list_id INTEGER NOT NULL REFERENCES shopping_list(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    checked INTEGER NOT NULL DEFAULT 0,
    checked_at TEXT
);
CREATE TABLE IF NOT EXISTS item_history (
    name TEXT PRIMARY KEY,
    category TEXT,
    use_count INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS task_template (
    id INTEGER PRIMARY KEY,
    title TEXT NOT NULL,
    person_ids TEXT NOT NULL DEFAULT '[]',
    recurrence TEXT NOT NULL DEFAULT 'none',
    recurrence_param INTEGER,
    active INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS task (
    id INTEGER PRIMARY KEY,
    template_id INTEGER REFERENCES task_template(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    person_ids TEXT NOT NULL DEFAULT '[]',
    due_date TEXT,
    done INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT
);
CREATE TABLE IF NOT EXISTS meal (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    note TEXT,
    url TEXT,
    ingredients TEXT
);
CREATE TABLE IF NOT EXISTS notification_settings (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    enabled INTEGER NOT NULL DEFAULT 0,
    notify_service TEXT NOT NULL DEFAULT '',
    task_reminder_time TEXT NOT NULL DEFAULT '08:00',
    event_lead_minutes INTEGER NOT NULL DEFAULT 30
);
CREATE TABLE IF NOT EXISTS notification_sent (
    key TEXT PRIMARY KEY,
    sent_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS calendar_settings (
    entity_id TEXT PRIMARY KEY,
    enabled INTEGER NOT NULL DEFAULT 1,
    color TEXT NOT NULL DEFAULT '#e8743b'
);
"""


async def _migrate(db: aiosqlite.Connection) -> None:
    # notification_settings: einzelner notify_service → JSON-Liste notify_services
    cur = await db.execute("PRAGMA table_info(notification_settings)")
    cols = [r[1] for r in await cur.fetchall()]
    if "notify_services" not in cols:
        await db.execute(
            "ALTER TABLE notification_settings "
            "ADD COLUMN notify_services TEXT NOT NULL DEFAULT '[]'"
        )
        await db.execute(
            "UPDATE notification_settings SET notify_services = json_array(notify_service) "
            "WHERE notify_service != ''"
        )
    # meal: Zutaten als JSON-Liste
    cur = await db.execute("PRAGMA table_info(meal)")
    cols = [r[1] for r in await cur.fetchall()]
    if "ingredients" not in cols:
        await db.execute("ALTER TABLE meal ADD COLUMN ingredients TEXT")
    # calendar_settings aus den alten Person↔Kalender-Zuordnungen befüllen
    cur = await db.execute("SELECT COUNT(*) FROM calendar_settings")
    (count,) = await cur.fetchone()
    if count == 0:
        cur = await db.execute(
            "SELECT calendar_entity_id, color FROM person WHERE calendar_entity_id IS NOT NULL"
        )
        for entity_id, color in await cur.fetchall():
            await db.execute(
                "INSERT OR IGNORE INTO calendar_settings (entity_id, enabled, color) "
                "VALUES (?, 1, ?)",
                (entity_id, color),
            )


async def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await _migrate(db)
        # Default list so the app is usable immediately
        cur = await db.execute("SELECT COUNT(*) FROM shopping_list")
        (count,) = await cur.fetchone()
        if count == 0:
            await db.execute(
                "INSERT INTO shopping_list (name, icon, sort_order) VALUES ('Supermarkt', '🛒', 0)"
            )
        await db.commit()


def connect() -> aiosqlite.Connection:
    conn = aiosqlite.connect(DB_PATH)
    return conn


async def open_db() -> aiosqlite.Connection:
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    return db
