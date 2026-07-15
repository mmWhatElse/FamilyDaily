"""Editable recipe collection for meal planning."""

import json

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ws import broadcaster

router = APIRouter(prefix="/api/recipes", tags=["recipes"])
CATEGORIES = {"breakfast", "main", "snack"}


class RecipeIn(BaseModel):
    name: str
    category: str
    calories: int
    protein: int | None = None
    ingredients: list[str]
    note: str | None = None


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
    return name, category, data.calories, data.protein, json.dumps(ingredients, ensure_ascii=False), data.note


def _row(r) -> dict:
    item = dict(r)
    try:
        item["ingredients"] = json.loads(item.get("ingredients") or "[]")
    except (TypeError, ValueError):
        item["ingredients"] = []
    return item


@router.get("")
async def get_recipes(category: str | None = None, q: str = ""):
    params: list[object] = []
    where: list[str] = []
    if category:
        where.append("category = ?")
        params.append(category)
    if q.strip():
        where.append("(name LIKE ? COLLATE NOCASE OR ingredients LIKE ? COLLATE NOCASE)")
        needle = f"%{q.strip()}%"
        params.extend((needle, needle))
    sql = "SELECT * FROM recipe"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY name COLLATE NOCASE"
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
            "INSERT INTO recipe (name, category, calories, protein, ingredients, note) VALUES (?, ?, ?, ?, ?, ?)",
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
            "UPDATE recipe SET name=?, category=?, calories=?, protein=?, ingredients=?, note=?, updated_at=CURRENT_TIMESTAMP WHERE id=?",
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
