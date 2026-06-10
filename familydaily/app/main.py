"""FamilyDaily — HA addon backend (M1 skeleton)."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import aiosqlite
import httpx
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

DATA_DIR = Path(os.environ.get("FAMILYDAILY_DATA", "/data"))
DB_PATH = DATA_DIR / "familydaily.db"

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_API = "http://supervisor/core/api"

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
    url TEXT
);
"""


@asynccontextmanager
async def lifespan(app: FastAPI):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(SCHEMA)
        await db.commit()
    yield


app = FastAPI(title="FamilyDaily", lifespan=lifespan)


@app.get("/api/health")
async def health():
    return {"status": "ok", "db": DB_PATH.exists()}


@app.get("/api/ha/status")
async def ha_status():
    """Verify the Supervisor token can reach the HA core API and list calendars."""
    if not SUPERVISOR_TOKEN:
        return {"connected": False, "error": "SUPERVISOR_TOKEN fehlt (läuft nicht als Addon?)"}
    headers = {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{HA_API}/calendars", headers=headers)
            resp.raise_for_status()
            calendars = resp.json()
        except httpx.HTTPError as exc:
            return {"connected": False, "error": str(exc)}
    return {"connected": True, "calendars": calendars}


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


@app.get("/{path:path}")
async def spa(path: str):
    """Serve the frontend; unknown paths fall back to index.html (SPA routing)."""
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(STATIC_DIR / "index.html")
