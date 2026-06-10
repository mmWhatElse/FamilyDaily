"""FamilyDaily — HA addon backend."""

import os
from contextlib import asynccontextmanager
from pathlib import Path

import httpx
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import DB_PATH, init_db
from .shopping import router as shopping_router
from .ws import broadcaster

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_API = "http://supervisor/core/api"


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


app = FastAPI(title="FamilyDaily", lifespan=lifespan)
app.include_router(shopping_router)


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


@app.get("/{path:path}")
async def spa(path: str):
    """Serve the frontend; unknown paths fall back to index.html (SPA routing)."""
    candidate = STATIC_DIR / path
    if path and candidate.is_file():
        return FileResponse(candidate)
    return FileResponse(STATIC_DIR / "index.html")
