"""Home Assistant API bridge (REST + WebSocket) via Supervisor token."""

import json
import os

import httpx
import websockets

SUPERVISOR_TOKEN = os.environ.get("SUPERVISOR_TOKEN")
HA_REST = "http://supervisor/core/api"
HA_WS = "ws://supervisor/core/websocket"


class HAError(Exception):
    pass


def _headers() -> dict:
    if not SUPERVISOR_TOKEN:
        raise HAError("SUPERVISOR_TOKEN fehlt (läuft nicht als Addon?)")
    return {"Authorization": f"Bearer {SUPERVISOR_TOKEN}"}


async def ha_get(path: str, params: dict | None = None):
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(f"{HA_REST}{path}", headers=_headers(), params=params)
        resp.raise_for_status()
        return resp.json()


async def ha_post(path: str, payload: dict):
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(f"{HA_REST}{path}", headers=_headers(), json=payload)
        resp.raise_for_status()
        return resp.json() if resp.content else None


async def ha_ws_command(msg_type: str, payload: dict):
    """Single command against the HA WebSocket API (needed for calendar delete)."""
    if not SUPERVISOR_TOKEN:
        raise HAError("SUPERVISOR_TOKEN fehlt (läuft nicht als Addon?)")
    async with websockets.connect(HA_WS, open_timeout=10) as ws:
        first = json.loads(await ws.recv())
        if first.get("type") == "auth_required":
            await ws.send(json.dumps({"type": "auth", "access_token": SUPERVISOR_TOKEN}))
            auth = json.loads(await ws.recv())
            if auth.get("type") != "auth_ok":
                raise HAError("HA WebSocket-Authentifizierung fehlgeschlagen")
        await ws.send(json.dumps({"id": 1, "type": msg_type, **payload}))
        while True:
            msg = json.loads(await ws.recv())
            if msg.get("id") == 1:
                if not msg.get("success", False):
                    err = msg.get("error", {}).get("message", "unbekannter Fehler")
                    raise HAError(f"HA: {err}")
                return msg.get("result")
