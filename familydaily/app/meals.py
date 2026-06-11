"""Mahlzeiten — one dinner entry per day."""

from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ws import broadcaster

router = APIRouter(prefix="/api/meals", tags=["meals"])


class MealIn(BaseModel):
    title: str
    note: str | None = None
    url: str | None = None


@router.get("")
async def get_meals(start: str, end: str):
    db = await open_db()
    try:
        cur = await db.execute(
            "SELECT * FROM meal WHERE date >= ? AND date <= ? ORDER BY date",
            (start, end),
        )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.put("/{day}")
async def set_meal(day: str, data: MealIn):
    title = data.title.strip()
    if not title:
        raise HTTPException(422, "Titel darf nicht leer sein")
    db = await open_db()
    try:
        await db.execute(
            """INSERT INTO meal (date, title, note, url) VALUES (?, ?, ?, ?)
               ON CONFLICT(date) DO UPDATE SET
                 title = excluded.title, note = excluded.note, url = excluded.url""",
            (day, title, data.note, data.url),
        )
        await db.commit()
        await broadcaster.broadcast({"type": "meals"})
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/{day}", status_code=204)
async def delete_meal(day: str):
    db = await open_db()
    try:
        await db.execute("DELETE FROM meal WHERE date = ?", (day,))
        await db.commit()
        await broadcaster.broadcast({"type": "meals"})
    finally:
        await db.close()


@router.post("/copy-last-week")
async def copy_last_week():
    """Copy last week's meals onto this week (only into empty days)."""
    monday = date.today() - timedelta(days=date.today().weekday())
    db = await open_db()
    try:
        copied = 0
        for offset in range(7):
            target = monday + timedelta(days=offset)
            source = target - timedelta(days=7)
            cur = await db.execute("SELECT * FROM meal WHERE date = ?", (source.isoformat(),))
            src = await cur.fetchone()
            if not src:
                continue
            cur = await db.execute("SELECT 1 FROM meal WHERE date = ?", (target.isoformat(),))
            if await cur.fetchone():
                continue
            await db.execute(
                "INSERT INTO meal (date, title, note, url) VALUES (?, ?, ?, ?)",
                (target.isoformat(), src["title"], src["note"], src["url"]),
            )
            copied += 1
        await db.commit()
        await broadcaster.broadcast({"type": "meals"})
        return {"copied": copied}
    finally:
        await db.close()
