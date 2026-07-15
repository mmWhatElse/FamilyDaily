"""Weekly meal plan with one entry per category and day."""

import json
from datetime import date, timedelta

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ws import broadcaster

router = APIRouter(prefix="/api/meals", tags=["meals"])


class MealIn(BaseModel):
    title: str
    category: str = "dinner"
    note: str | None = None
    url: str | None = None
    ingredients: list[str] | None = None
    calories: int | None = None
    recipe_id: int | None = None


CATEGORIES = {"breakfast", "lunch", "dinner", "snack"}


def _row_to_meal(r) -> dict:
    m = dict(r)
    try:
        m["ingredients"] = json.loads(m.get("ingredients") or "[]")
    except (TypeError, ValueError):
        m["ingredients"] = []
    return m


def _clean_ingredients(items: list[str] | None) -> str | None:
    cleaned = [s.strip() for s in (items or []) if s.strip()]
    return json.dumps(cleaned, ensure_ascii=False) if cleaned else None


@router.get("")
async def get_meals(start: str, end: str, category: str | None = None):
    db = await open_db()
    try:
        if category:
            cur = await db.execute(
                "SELECT * FROM meal WHERE date >= ? AND date <= ? AND category = ? ORDER BY date",
                (start, end, category),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM meal WHERE date >= ? AND date <= ? ORDER BY date, category",
                (start, end),
            )
        return [_row_to_meal(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.get("/dish-ingredients")
async def dish_ingredients(title: str = ""):
    """Zuletzt gespeicherte Zutaten für ein Gericht (zur Wiederverwendung)."""
    title = title.strip()
    if not title:
        return {"ingredients": []}
    db = await open_db()
    try:
        cur = await db.execute(
            "SELECT ingredients FROM meal "
            "WHERE title = ? COLLATE NOCASE AND ingredients IS NOT NULL "
            "ORDER BY date DESC LIMIT 1",
            (title,),
        )
        row = await cur.fetchone()
        try:
            ingredients = json.loads(row["ingredients"]) if row else []
        except (TypeError, ValueError):
            ingredients = []
        return {"ingredients": ingredients}
    finally:
        await db.close()


@router.put("/{day}")
async def set_meal(day: str, data: MealIn):
    title = data.title.strip()
    if not title:
        raise HTTPException(422, "Titel darf nicht leer sein")
    category = data.category.strip().lower()
    if category not in CATEGORIES:
        raise HTTPException(422, "Unbekannte Mahlzeit-Kategorie")
    db = await open_db()
    try:
        await db.execute(
            """INSERT INTO meal
                 (date, category, title, note, url, ingredients, calories, recipe_id)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)
               ON CONFLICT(date, category) DO UPDATE SET
                 title = excluded.title, note = excluded.note, url = excluded.url,
                 ingredients = excluded.ingredients, calories = excluded.calories,
                 recipe_id = excluded.recipe_id""",
            (day, category, title, data.note, data.url,
             _clean_ingredients(data.ingredients), data.calories, data.recipe_id),
        )
        await db.commit()
        await broadcaster.broadcast({"type": "meals"})
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/{day}", status_code=204)
async def delete_meal(day: str, category: str = "dinner"):
    db = await open_db()
    try:
        await db.execute("DELETE FROM meal WHERE date = ? AND category = ?", (day, category))
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
            for src in await cur.fetchall():
                cur = await db.execute(
                    "SELECT 1 FROM meal WHERE date = ? AND category = ?",
                    (target.isoformat(), src["category"]),
                )
                if await cur.fetchone():
                    continue
                await db.execute(
                    """INSERT INTO meal
                       (date, category, title, note, url, ingredients, calories, recipe_id)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (target.isoformat(), src["category"], src["title"], src["note"],
                     src["url"], src["ingredients"], src["calories"], src["recipe_id"]),
                )
                copied += 1
        await db.commit()
        await broadcaster.broadcast({"type": "meals"})
        return {"copied": copied}
    finally:
        await db.close()
