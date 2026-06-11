"""Kalender — reads/writes HA calendar entities (Local Calendar in V1)."""

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ha import HAError, ha_get, ha_post, ha_ws_command
from .ws import broadcaster

router = APIRouter(prefix="/api/calendar", tags=["calendar"])


class EventIn(BaseModel):
    entity_id: str
    summary: str
    start: str  # ISO datetime, or ISO date if all_day
    end: str
    all_day: bool = False
    description: str | None = None


class EventDelete(BaseModel):
    entity_id: str
    uid: str
    recurrence_id: str | None = None


async def _person_map() -> dict:
    db = await open_db()
    try:
        cur = await db.execute(
            "SELECT name, color, emoji, calendar_entity_id FROM person "
            "WHERE calendar_entity_id IS NOT NULL"
        )
        return {r["calendar_entity_id"]: dict(r) for r in await cur.fetchall()}
    finally:
        await db.close()


@router.get("/events")
async def get_events(start: str, end: str):
    """All events from all mapped person calendars (plus unmapped HA calendars)."""
    persons = await _person_map()
    try:
        calendars = await ha_get("/calendars")
    except (HAError, httpx.HTTPError) as exc:
        raise HTTPException(502, f"Home Assistant nicht erreichbar: {exc}")

    events = []
    for c in calendars:
        entity_id = c["entity_id"]
        try:
            raw = await ha_get(
                f"/calendars/{entity_id}", params={"start": start, "end": end}
            )
        except (HAError, httpx.HTTPError):
            continue
        person = persons.get(entity_id)
        for ev in raw:
            ev_start = ev.get("start", {})
            ev_end = ev.get("end", {})
            events.append({
                "entity_id": entity_id,
                "uid": ev.get("uid"),
                "recurrence_id": ev.get("recurrence_id"),
                "summary": ev.get("summary", ""),
                "description": ev.get("description"),
                "start": ev_start.get("dateTime") or ev_start.get("date"),
                "end": ev_end.get("dateTime") or ev_end.get("date"),
                "all_day": "date" in ev_start,
                "person": person["name"] if person else c.get("name", entity_id),
                "color": person["color"] if person else "#9aa0a6",
                "emoji": person["emoji"] if person else None,
            })
    events.sort(key=lambda e: (e["start"] or "", e["summary"]))
    return events


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
