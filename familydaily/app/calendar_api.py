"""Kalender — reads/writes HA calendar entities (Local Calendar in V1).

Welche Kalender die App nutzt (und in welcher Farbe), steht in calendar_settings —
unabhängig von Personen. Neue HA-Kalender werden beim ersten Auflisten automatisch
registriert und sind standardmäßig aktiv.
"""

from datetime import datetime

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ha import HAError, ha_get, ha_post, ha_ws_command
from .ws import broadcaster

router = APIRouter(prefix="/api/calendar", tags=["calendar"])

PALETTE = [
    "#e8743b", "#4a90d9", "#2a9e67", "#9b59b6",
    "#e84393", "#f39c12", "#16a085", "#c0392b",
]


class EventIn(BaseModel):
    entity_id: str
    summary: str
    start: str  # ISO datetime, or ISO date if all_day
    end: str
    all_day: bool = False
    description: str | None = None


class EventUpdate(EventIn):
    uid: str
    recurrence_id: str | None = None


class EventDelete(BaseModel):
    entity_id: str
    uid: str
    recurrence_id: str | None = None


class CalendarPatch(BaseModel):
    enabled: bool | None = None
    color: str | None = None


async def _merged_calendars(db) -> list[dict]:
    """HA calendars merged with stored settings; unknown ones get auto-registered."""
    ha_cals = await ha_get("/calendars")
    cur = await db.execute("SELECT * FROM calendar_settings")
    settings = {r["entity_id"]: dict(r) for r in await cur.fetchall()}
    result = []
    added = 0
    for c in ha_cals:
        entity_id = c["entity_id"]
        s = settings.get(entity_id)
        if not s:
            color = PALETTE[(len(settings) + added) % len(PALETTE)]
            await db.execute(
                "INSERT OR IGNORE INTO calendar_settings (entity_id, enabled, color) "
                "VALUES (?, 1, ?)",
                (entity_id, color),
            )
            s = {"enabled": 1, "color": color}
            added += 1
        result.append({
            "entity_id": entity_id,
            "name": c.get("name") or entity_id,
            "enabled": bool(s["enabled"]),
            "color": s["color"],
        })
    if added:
        await db.commit()
    return result


@router.get("/calendars")
async def list_calendars():
    db = await open_db()
    try:
        return await _merged_calendars(db)
    except (HAError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Home Assistant nicht erreichbar: {exc}")
    finally:
        await db.close()


@router.patch("/calendars/{entity_id}")
async def patch_calendar(entity_id: str, data: CalendarPatch):
    db = await open_db()
    try:
        await db.execute(
            "INSERT OR IGNORE INTO calendar_settings (entity_id) VALUES (?)", (entity_id,)
        )
        if data.enabled is not None:
            await db.execute(
                "UPDATE calendar_settings SET enabled = ? WHERE entity_id = ?",
                (int(data.enabled), entity_id),
            )
        if data.color is not None:
            await db.execute(
                "UPDATE calendar_settings SET color = ? WHERE entity_id = ?",
                (data.color, entity_id),
            )
        await db.commit()
    finally:
        await db.close()
    await broadcaster.broadcast({"type": "calendar"})
    return {"ok": True}


@router.get("/events")
async def get_events(start: str, end: str):
    """All events from the enabled calendars, colored per calendar."""
    db = await open_db()
    try:
        calendars = await _merged_calendars(db)
    except (HAError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Home Assistant nicht erreichbar: {exc}")
    finally:
        await db.close()

    events = []
    for c in calendars:
        if not c["enabled"]:
            continue
        try:
            raw = await ha_get(
                f"/calendars/{c['entity_id']}", params={"start": start, "end": end}
            )
        except (HAError, httpx.HTTPError):
            continue
        for ev in raw:
            ev_start = ev.get("start", {})
            ev_end = ev.get("end", {})
            events.append({
                "entity_id": c["entity_id"],
                "uid": ev.get("uid"),
                "recurrence_id": ev.get("recurrence_id"),
                "summary": ev.get("summary", ""),
                "description": ev.get("description"),
                "start": ev_start.get("dateTime") or ev_start.get("date"),
                "end": ev_end.get("dateTime") or ev_end.get("date"),
                "all_day": "date" in ev_start,
                "calendar": c["name"],
                "color": c["color"],
            })
    events.sort(key=lambda e: (e["start"] or "", e["summary"]))
    return events


def _aware_iso(value: str) -> str:
    """Naive ISO datetime → local-timezone-aware (HA WS schema requires tzinfo)."""
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.astimezone()
    return dt.isoformat()


@router.post("/events", status_code=201)
async def create_event(data: EventIn):
    payload: dict = {"entity_id": data.entity_id, "summary": data.summary.strip()}
    if data.description:
        payload["description"] = data.description
    if data.all_day:
        payload["start_date"] = data.start
        payload["end_date"] = data.end
    else:
        payload["start_date_time"] = data.start
        payload["end_date_time"] = data.end
    try:
        await ha_post("/services/calendar/create_event", payload)
    except (HAError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Termin konnte nicht angelegt werden: {exc}")
    await broadcaster.broadcast({"type": "calendar"})
    return {"ok": True}


@router.post("/events/update")
async def update_event(data: EventUpdate):
    """Update via HA WebSocket API (supported by Local Calendar)."""
    event: dict = {"summary": data.summary.strip()}
    if data.all_day:
        event["dtstart"] = data.start
        event["dtend"] = data.end
    else:
        event["dtstart"] = _aware_iso(data.start)
        event["dtend"] = _aware_iso(data.end)
    if data.description:
        event["description"] = data.description
    payload: dict = {"entity_id": data.entity_id, "uid": data.uid, "event": event}
    if data.recurrence_id:
        payload["recurrence_id"] = data.recurrence_id
        payload["recurrence_range"] = ""
    try:
        await ha_ws_command("calendar/event/update", payload)
    except (HAError, Exception) as exc:
        raise HTTPException(502, f"Termin konnte nicht geändert werden: {exc}")
    await broadcaster.broadcast({"type": "calendar"})
    return {"ok": True}


@router.post("/events/delete")
async def delete_event(data: EventDelete):
    """Delete via HA WebSocket API (supported by Local Calendar)."""
    payload = {"entity_id": data.entity_id, "uid": data.uid}
    if data.recurrence_id:
        payload["recurrence_id"] = data.recurrence_id
        payload["recurrence_range"] = ""
    try:
        await ha_ws_command("calendar/event/delete", payload)
    except (HAError, Exception) as exc:
        raise HTTPException(502, f"Termin konnte nicht gelöscht werden: {exc}")
    await broadcaster.broadcast({"type": "calendar"})
    return {"ok": True}
