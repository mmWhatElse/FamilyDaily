"""Familienmitglieder — Personen-API inkl. Gerätezuordnung."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ha import HAError, ha_get
from .ws import broadcaster

router = APIRouter(prefix="/api/persons", tags=["persons"])


class PersonIn(BaseModel):
    name: str
    color: str = "#4a90d9"
    emoji: str | None = None
    calendar_entity_id: str | None = None
    notify_services: list[str] = []


class PersonPatch(BaseModel):
    name: str | None = None
    color: str | None = None
    emoji: str | None = None
    calendar_entity_id: str | None = None
    notify_services: list[str] | None = None


def _person_dict(row) -> dict:
    person = dict(row)
    try:
        person["notify_services"] = json.loads(person.get("notify_services") or "[]")
    except (TypeError, ValueError):
        person["notify_services"] = []
    return person


@router.get("")
async def get_persons():
    db = await open_db()
    try:
        cur = await db.execute("SELECT * FROM person ORDER BY id")
        return [_person_dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.post("", status_code=201)
async def create_person(data: PersonIn):
    db = await open_db()
    try:
        cur = await db.execute(
            "INSERT INTO person "
            "(name, color, emoji, calendar_entity_id, notify_services) "
            "VALUES (?, ?, ?, ?, ?)",
            (data.name.strip(), data.color, data.emoji, data.calendar_entity_id,
             json.dumps(data.notify_services)),
        )
        await db.commit()
        await broadcaster.broadcast({"type": "persons"})
        return {"id": cur.lastrowid}
    finally:
        await db.close()


@router.patch("/{person_id}")
async def patch_person(person_id: int, data: PersonPatch):
    db = await open_db()
    try:
        cur = await db.execute("SELECT id FROM person WHERE id = ?", (person_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Person nicht gefunden")
        for field in ("name", "color", "emoji", "calendar_entity_id", "notify_services"):
            value = getattr(data, field)
            if value is not None:
                if field == "notify_services":
                    value = json.dumps(value)
                await db.execute(
                    f"UPDATE person SET {field} = ? WHERE id = ?", (value, person_id)
                )
        await db.commit()
        await broadcaster.broadcast({"type": "persons"})
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/{person_id}", status_code=204)
async def delete_person(person_id: int):
    db = await open_db()
    try:
        await db.execute("DELETE FROM person WHERE id = ?", (person_id,))
        await db.commit()
        await broadcaster.broadcast({"type": "persons"})
    finally:
        await db.close()


@router.get("/ha-calendars")
async def ha_calendars():
    """List calendar entities available in HA (for the mapping dropdown)."""
    try:
        return await ha_get("/calendars")
    except (HAError, Exception) as exc:
        return {"error": str(exc)}
