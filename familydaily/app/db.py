"""SQLite helpers for FamilyDaily."""

import os
import json
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
    calendar_entity_id TEXT,
    notify_services TEXT NOT NULL DEFAULT '[]'
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
    start_date TEXT,
    end_date TEXT,
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
CREATE TABLE IF NOT EXISTS recipe (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    calories INTEGER NOT NULL,
    protein INTEGER,
    ingredients TEXT NOT NULL DEFAULT '[]',
    note TEXT,
    favorite INTEGER NOT NULL DEFAULT 0,
    tags TEXT NOT NULL DEFAULT '[]',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS meal (
    id INTEGER PRIMARY KEY,
    date TEXT NOT NULL,
    category TEXT NOT NULL DEFAULT 'dinner',
    title TEXT NOT NULL,
    note TEXT,
    url TEXT,
    ingredients TEXT,
    calories INTEGER,
    recipe_id INTEGER REFERENCES recipe(id) ON DELETE SET NULL,
    UNIQUE(date, category)
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
CREATE TABLE IF NOT EXISTS app_settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL DEFAULT ''
);
"""


async def _migrate(db: aiosqlite.Connection) -> None:
    cur = await db.execute("PRAGMA table_info(person)")
    person_cols = [r[1] for r in await cur.fetchall()]
    if "notify_services" not in person_cols:
        await db.execute(
            "ALTER TABLE person "
            "ADD COLUMN notify_services TEXT NOT NULL DEFAULT '[]'"
        )
    cur = await db.execute("PRAGMA table_info(recipe)")
    recipe_cols = [r[1] for r in await cur.fetchall()]
    if "favorite" not in recipe_cols:
        await db.execute("ALTER TABLE recipe ADD COLUMN favorite INTEGER NOT NULL DEFAULT 0")
    if "tags" not in recipe_cols:
        await db.execute("ALTER TABLE recipe ADD COLUMN tags TEXT NOT NULL DEFAULT '[]'")
    # Mittag und Abend sind in der Rezeptbox dieselbe Art Hauptgericht.
    await db.execute(
        "UPDATE recipe SET category = 'main' WHERE category IN ('lunch', 'dinner')"
    )
    cur = await db.execute("PRAGMA table_info(task_template)")
    template_cols = [r[1] for r in await cur.fetchall()]
    if "start_date" not in template_cols:
        await db.execute("ALTER TABLE task_template ADD COLUMN start_date TEXT")
        await db.execute(
            "UPDATE task_template SET start_date = COALESCE("
            "(SELECT MIN(due_date) FROM task WHERE task.template_id = task_template.id), "
            "date('now'))"
        )
    if "end_date" not in template_cols:
        await db.execute("ALTER TABLE task_template ADD COLUMN end_date TEXT")
    # task: bewusst verworfene Einzelvorkommen wiederkehrender Aufgaben ausblenden,
    # ohne dass die Materialisierung sie beim nächsten Laden erneut anlegt.
    cur = await db.execute("PRAGMA table_info(task)")
    task_cols = [r[1] for r in await cur.fetchall()]
    if "skipped" not in task_cols:
        await db.execute("ALTER TABLE task ADD COLUMN skipped INTEGER NOT NULL DEFAULT 0")
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
    # meal: legacy one-dinner-per-day table -> four meal slots per day
    cur = await db.execute("PRAGMA table_info(meal)")
    cols = [r[1] for r in await cur.fetchall()]
    if "category" not in cols:
        await db.execute("ALTER TABLE meal RENAME TO meal_legacy")
        await db.execute("""CREATE TABLE meal (
            id INTEGER PRIMARY KEY,
            date TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'dinner',
            title TEXT NOT NULL,
            note TEXT,
            url TEXT,
            ingredients TEXT,
            calories INTEGER,
            recipe_id INTEGER REFERENCES recipe(id) ON DELETE SET NULL,
            UNIQUE(date, category)
        )""")
        legacy_cols = set(cols)
        ingredients_expr = "ingredients" if "ingredients" in legacy_cols else "NULL"
        await db.execute(
            "INSERT INTO meal (id, date, category, title, note, url, ingredients) "
            f"SELECT id, date, 'dinner', title, note, url, {ingredients_expr} FROM meal_legacy"
        )
        await db.execute("DROP TABLE meal_legacy")
    else:
        if "calories" not in cols:
            await db.execute("ALTER TABLE meal ADD COLUMN calories INTEGER")
        if "recipe_id" not in cols:
            await db.execute("ALTER TABLE meal ADD COLUMN recipe_id INTEGER REFERENCES recipe(id) ON DELETE SET NULL")
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
        cur = await db.execute("SELECT COUNT(*) FROM recipe")
        (count,) = await cur.fetchone()
        if count == 0:
            from .recipe_seed import RECIPES, RECIPE_TAGS
            await db.executemany(
                "INSERT INTO recipe (name, category, calories, protein, ingredients, tags) VALUES (?, ?, ?, ?, ?, ?)",
                [(name, category, calories, protein, json.dumps(ingredients, ensure_ascii=False),
                  json.dumps(RECIPE_TAGS.get(name, []), ensure_ascii=False))
                 for name, category, calories, protein, ingredients in RECIPES],
            )
        # Starter-Tags auch bei bestehenden Installationen ergänzen.
        from .recipe_seed import RECIPE_TAGS
        for name, tags in RECIPE_TAGS.items():
            await db.execute(
                "UPDATE recipe SET tags = ? WHERE name = ? COLLATE NOCASE AND (tags IS NULL OR tags = '[]')",
                (json.dumps(tags, ensure_ascii=False), name),
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
