"""FamilyDaily — HA addon backend."""

import asyncio
import os
from contextlib import asynccontextmanager, suppress
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles

from .calendar_api import router as calendar_router
from .db import DB_PATH, init_db
from .meals import router as meals_router
from .notifications import notification_loop
from .notifications import router as notifications_router
from .persons import router as persons_router
from .shopping import router as shopping_router
from .tasks import router as tasks_router
from .ws import broadcaster

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_API = "http://supervisor/core/api"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    task = asyncio.create_task(notification_loop())
    yield
    task.cancel()
    with suppress(asyncio.CancelledError):
        await task


app = FastAPI(title="FamilyDaily", lifespan=lifespan)
app.include_router(shopping_router)
app.include_router(tasks_router)
app.include_router(persons_router)
app.include_router(calendar_router)
app.include_router(meals_router)
app.include_router(notifications_router)


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


_weather_entity: str | None = None


@app.get("/api/weather")
async def weather():
    """Aktuelles Wetter aus der ersten weather.*-Entität in HA (für die Heute-Begrüßung)."""
    global _weather_entity
    from .ha import ha_get

    try:
        state = None
        if _weather_entity:
            try:
                state = await ha_get(f"/states/{_weather_entity}")
            except Exception:
                _weather_entity = None
        if state is None:
            states = await ha_get("/states")
            state = next(
                (s for s in states if s.get("entity_id", "").startswith("weather.")), None
            )
            if state:
                _weather_entity = state["entity_id"]
        if not state:
            return {"available": False}
        attrs = state.get("attributes", {})
        return {
            "available": True,
            "condition": state.get("state"),
            "temperature": attrs.get("temperature"),
        }
    except Exception:
        return {"available": False}


@app.get("/api/settings")
async def get_app_settings():
    from .db import open_db
    db = await open_db()
    try:
        cur = await db.execute("SELECT key, value FROM app_settings")
        rows = await cur.fetchall()
        return {r["key"]: r["value"] for r in rows}
    finally:
        await db.close()


@app.patch("/api/settings")
async def patch_app_settings(data: dict):
    from .db import open_db
    db = await open_db()
    try:
        for key, value in data.items():
            await db.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, str(value)),
            )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@app.get("/api/ha/entity")
async def ha_entity_state(entity_id: str):
    from .ha import ha_get
    try:
        state = await ha_get(f"/states/{entity_id}")
        return {"available": True, "state": state["state"]}
    except Exception:
        return {"available": False}


@app.websocket("/api/ws")
async def websocket_endpoint(ws: WebSocket):
    await broadcaster.connect(ws)
    try:
        while True:
            await ws.receive_text()  # keepalive pings from clients
    except WebSocketDisconnect:
        broadcaster.disconnect(ws)


STATIC_DIR = Path(__file__).parent / "static"
app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")


# Optionaler, rein lokaler Aufgabenton. Die Datei liegt im Add-on-Konfigurationsordner
# (/config) und wird deshalb weder mit dem Add-on ausgeliefert noch in Git eingecheckt.
CUSTOM_SOUND_DIR = Path(os.environ.get("FAMILYDAILY_SOUND_DIR", "/config"))
CUSTOM_SOUND_NAMES = ("task-level-up.mp3", "task-level-up.ogg", "task-level-up.wav")


@app.get("/api/sounds/task-level-up")
async def task_level_up_sound():
    for name in CUSTOM_SOUND_NAMES:
        candidate = CUSTOM_SOUND_DIR / name
        if candidate.is_file():
            return FileResponse(candidate)
    return Response(status_code=404)


# index.html immer revalidieren — sonst behält der Browser den alten ?v=-Verweis
# und lädt das neue app.js/style.css nach einem Update nicht. Die Assets selbst
# sind über ?v=<version> versioniert und dürfen gecacht werden.
_HTML_NO_CACHE = {"Cache-Control": "no-cache"}


@app.get("/{path:path}")
async def spa(path: str):
    """Serve the frontend; unknown paths fall back to index.html (SPA routing)."""
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        headers = _HTML_NO_CACHE if candidate.suffix in (".html", ".json") else None
        return FileResponse(candidate, headers=headers)
    return FileResponse(STATIC_DIR / "index.html", headers=_HTML_NO_CACHE)
