"""Editable recipe collection for meal planning."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .db import open_db
from .ws import broadcaster

router = APIRouter(prefix="/api/recipes", tags=["recipes"])
CATEGORIES = {"breakfast", "main", "snack"}
TAG_KEYS = {"quick", "family", "mealprep", "vegetarian", "takeaway", "weekend"}


class RecipeIn(BaseModel):
    name: str
    category: str
    calories: int
    protein: int | None = None
    ingredients: list[str]
    note: str | None = None
    tags: list[str] = Field(default_factory=list)


class FavoriteIn(BaseModel):
    favorite: bool


def _clean(data: RecipeIn) -> tuple:
    name = data.name.strip()
    category = data.category.strip().lower()
    ingredients = [item.strip() for item in data.ingredients if item.strip()]
    if not name:
        raise HTTPException(422, "Name darf nicht leer sein")
    if category not in CATEGORIES:
        raise HTTPException(422, "Unbekannte Mahlzeit-Kategorie")
    if data.calories < 0:
        raise HTTPException(422, "Kalorien dürfen nicht negativ sein")
    if not ingredients:
        raise HTTPException(422, "Mindestens eine Zutat ist erforderlich")
    tags = list(dict.fromkeys(tag.strip().lower() for tag in data.tags if tag.strip()))
    if set(tags) - TAG_KEYS:
        raise HTTPException(422, "Unbekannte Rezept-Tags")
    return (name, category, data.calories, data.protein,
            json.dumps(ingredients, ensure_ascii=False), data.note,
            json.dumps(tags, ensure_ascii=False))


def _row(r) -> dict:
    item = dict(r)
    try:
        item["ingredients"] = json.loads(item.get("ingredients") or "[]")
    except (TypeError, ValueError):
        item["ingredients"] = []
    try:
        item["tags"] = json.loads(item.get("tags") or "[]")
    except (TypeError, ValueError):
        item["tags"] = []
    item["favorite"] = bool(item.get("favorite"))
    return item


@router.get("")
async def get_recipes(category: str | None = None, q: str = ""):
    params: list[object] = []
    where: list[str] = []
    if category:
        where.append("r.category = ?")
        params.append(category)
    if q.strip():
        where.append("(r.name LIKE ? COLLATE NOCASE OR r.ingredients LIKE ? COLLATE NOCASE)")
        needle = f"%{q.strip()}%"
        params.extend((needle, needle))
    sql = """SELECT r.*,
                    (SELECT MAX(m.date) FROM meal m
                     WHERE m.date <= date('now', 'localtime')
                       AND (m.recipe_id = r.id OR
                            (m.recipe_id IS NULL AND m.title = r.name COLLATE NOCASE)))
                    AS last_cooked
             FROM recipe r"""
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY r.favorite DESC, r.name COLLATE NOCASE"
    db = await open_db()
    try:
        rows = await (await db.execute(sql, params)).fetchall()
        return [_row(r) for r in rows]
    finally:
        await db.close()


@router.post("", status_code=201)
async def create_recipe(data: RecipeIn):
    values = _clean(data)
    db = await open_db()
    try:
        cur = await db.execute(
            "INSERT INTO recipe (name, category, calories, protein, ingredients, note, tags) VALUES (?, ?, ?, ?, ?, ?, ?)",
            values,
        )
        await db.commit()
        await broadcaster.broadcast({"type": "recipes"})
        row = await (await db.execute("SELECT * FROM recipe WHERE id = ?", (cur.lastrowid,))).fetchone()
        return _row(row)
    finally:
        await db.close()


@router.put("/{recipe_id}")
async def update_recipe(recipe_id: int, data: RecipeIn):
    values = _clean(data)
    db = await open_db()
    try:
        cur = await db.execute(
            "UPDATE recipe SET name=?, category=?, calories=?, protein=?, ingredients=?, note=?, tags=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
            (*values, recipe_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Rezept nicht gefunden")
        await db.commit()
        await broadcaster.broadcast({"type": "recipes"})
        row = await (await db.execute("SELECT * FROM recipe WHERE id = ?", (recipe_id,))).fetchone()
        return _row(row)
    finally:
        await db.close()


@router.patch("/{recipe_id}/favorite")
async def set_favorite(recipe_id: int, data: FavoriteIn):
    db = await open_db()
    try:
        cur = await db.execute(
            "UPDATE recipe SET favorite = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (int(data.favorite), recipe_id),
        )
        if cur.rowcount == 0:
            raise HTTPException(404, "Rezept nicht gefunden")
        await db.commit()
        await broadcaster.broadcast({"type": "recipes"})
        return {"ok": True, "favorite": data.favorite}
    finally:
        await db.close()


@router.delete("/{recipe_id}", status_code=204)
async def delete_recipe(recipe_id: int):
    db = await open_db()
    try:
        cur = await db.execute("DELETE FROM recipe WHERE id = ?", (recipe_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Rezept nicht gefunden")
        await db.commit()
        await broadcaster.broadcast({"type": "recipes"})
    finally:
        await db.close()
