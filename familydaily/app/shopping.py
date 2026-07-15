"""Einkaufen — shopping lists API."""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ws import broadcaster

router = APIRouter(prefix="/api/shopping", tags=["shopping"])


class ListIn(BaseModel):
    name: str
    icon: str | None = None


class ItemIn(BaseModel):
    name: str
    category: str | None = None


class ItemPatch(BaseModel):
    name: str | None = None
    category: str | None = None
    checked: bool | None = None


class ItemBulkIn(BaseModel):
    names: list[str]


async def _notify(list_id: int) -> None:
    await broadcaster.broadcast({"type": "shopping", "list_id": list_id})


@router.get("/lists")
async def get_lists():
    db = await open_db()
    try:
        cur = await db.execute(
            """SELECT l.id, l.name, l.icon, l.sort_order,
                      SUM(CASE WHEN i.checked = 0 THEN 1 ELSE 0 END) AS open_count
               FROM shopping_list l
               LEFT JOIN shopping_item i ON i.list_id = l.id
               GROUP BY l.id ORDER BY l.sort_order, l.id"""
        )
        rows = await cur.fetchall()
        return [dict(r) | {"open_count": r["open_count"] or 0} for r in rows]
    finally:
        await db.close()


@router.post("/lists", status_code=201)
async def create_list(data: ListIn):
    db = await open_db()
    try:
        cur = await db.execute(
            "INSERT INTO shopping_list (name, icon, sort_order) "
            "VALUES (?, ?, (SELECT COALESCE(MAX(sort_order), 0) + 1 FROM shopping_list))",
            (data.name.strip(), data.icon),
        )
        await db.commit()
        await _notify(cur.lastrowid)
        return {"id": cur.lastrowid, "name": data.name.strip(), "icon": data.icon}
    finally:
        await db.close()


@router.delete("/lists/{list_id}", status_code=204)
async def delete_list(list_id: int):
    db = await open_db()
    try:
        await db.execute("DELETE FROM shopping_item WHERE list_id = ?", (list_id,))
        await db.execute("DELETE FROM shopping_list WHERE id = ?", (list_id,))
        await db.commit()
        await _notify(list_id)
    finally:
        await db.close()


@router.get("/lists/{list_id}/items")
async def get_items(list_id: int):
    db = await open_db()
    try:
        cur = await db.execute(
            "SELECT id, name, category, checked, checked_at FROM shopping_item "
            "WHERE list_id = ? ORDER BY checked, id DESC",
            (list_id,),
        )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.post("/lists/{list_id}/items", status_code=201)
async def add_item(list_id: int, data: ItemIn):
    name = data.name.strip()
    if not name:
        raise HTTPException(422, "Name darf nicht leer sein")
    db = await open_db()
    try:
        cur = await db.execute("SELECT id FROM shopping_list WHERE id = ?", (list_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Liste nicht gefunden")
        # If the same unchecked item already exists, do nothing (idempotent add)
        cur = await db.execute(
            "SELECT id FROM shopping_item WHERE list_id = ? AND checked = 0 AND name = ? COLLATE NOCASE",
            (list_id, name),
        )
        existing = await cur.fetchone()
        if existing:
            return {"id": existing["id"], "name": name, "duplicate": True}
        # Kategorie aus der Historie übernehmen, wenn keine mitgegeben wurde
        category = data.category
        if category is None:
            cur = await db.execute(
                "SELECT category FROM item_history WHERE name = ? COLLATE NOCASE",
                (name,),
            )
            hist = await cur.fetchone()
            if hist:
                category = hist["category"]
        cur = await db.execute(
            "INSERT INTO shopping_item (list_id, name, category) VALUES (?, ?, ?)",
            (list_id, name, category),
        )
        await db.execute(
            """INSERT INTO item_history (name, category, use_count) VALUES (?, ?, 1)
               ON CONFLICT(name) DO UPDATE SET
                 use_count = use_count + 1,
                 category = COALESCE(excluded.category, item_history.category)""",
            (name, data.category),
        )
        await db.commit()
        await _notify(list_id)
        return {"id": cur.lastrowid, "name": name, "category": category}
    finally:
        await db.close()


@router.post("/lists/{list_id}/items/bulk")
async def add_items_bulk(list_id: int, data: ItemBulkIn):
    """Add a recipe's ingredients in one request; open duplicates are skipped."""
    names = list(dict.fromkeys(name.strip() for name in data.names if name.strip()))
    db = await open_db()
    try:
        if not await (await db.execute(
            "SELECT id FROM shopping_list WHERE id = ?", (list_id,)
        )).fetchone():
            raise HTTPException(404, "Liste nicht gefunden")
        added = 0
        for name in names:
            existing = await (await db.execute(
                "SELECT id FROM shopping_item WHERE list_id = ? AND checked = 0 AND name = ? COLLATE NOCASE",
                (list_id, name),
            )).fetchone()
            if existing:
                continue
            history = await (await db.execute(
                "SELECT category FROM item_history WHERE name = ? COLLATE NOCASE", (name,)
            )).fetchone()
            category = history["category"] if history else None
            await db.execute(
                "INSERT INTO shopping_item (list_id, name, category) VALUES (?, ?, ?)",
                (list_id, name, category),
            )
            await db.execute(
                """INSERT INTO item_history (name, category, use_count) VALUES (?, ?, 1)
                   ON CONFLICT(name) DO UPDATE SET use_count = use_count + 1""",
                (name, category),
            )
            added += 1
        await db.commit()
        if added:
            await _notify(list_id)
        return {"added": added, "total": len(names)}
    finally:
        await db.close()


@router.patch("/items/{item_id}")
async def patch_item(item_id: int, data: ItemPatch):
    db = await open_db()
    try:
        cur = await db.execute(
            "SELECT id, list_id FROM shopping_item WHERE id = ?", (item_id,)
        )
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Artikel nicht gefunden")
        if data.name is not None:
            await db.execute(
                "UPDATE shopping_item SET name = ? WHERE id = ?",
                (data.name.strip(), item_id),
            )
        if data.category is not None:
            category = data.category or None  # "" entfernt die Kategorie
            await db.execute(
                "UPDATE shopping_item SET category = ? WHERE id = ?",
                (category, item_id),
            )
            # Zuordnung merken — künftige Käufe desselben Artikels landen direkt richtig
            cur = await db.execute(
                "SELECT name FROM shopping_item WHERE id = ?", (item_id,)
            )
            item = await cur.fetchone()
            if item:
                await db.execute(
                    """INSERT INTO item_history (name, category, use_count) VALUES (?, ?, 1)
                       ON CONFLICT(name) DO UPDATE SET category = excluded.category""",
                    (item["name"], category),
                )
        if data.checked is not None:
            checked_at = datetime.now(timezone.utc).isoformat() if data.checked else None
            await db.execute(
                "UPDATE shopping_item SET checked = ?, checked_at = ? WHERE id = ?",
                (int(data.checked), checked_at, item_id),
            )
        await db.commit()
        await _notify(row["list_id"])
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: int):
    db = await open_db()
    try:
        cur = await db.execute("SELECT list_id FROM shopping_item WHERE id = ?", (item_id,))
        row = await cur.fetchone()
        if row:
            await db.execute("DELETE FROM shopping_item WHERE id = ?", (item_id,))
            await db.commit()
            await _notify(row["list_id"])
    finally:
        await db.close()


@router.post("/lists/{list_id}/clear-checked")
async def clear_checked(list_id: int):
    db = await open_db()
    try:
        await db.execute(
            "DELETE FROM shopping_item WHERE list_id = ? AND checked = 1", (list_id,)
        )
        await db.commit()
        await _notify(list_id)
        return {"ok": True}
    finally:
        await db.close()


@router.get("/suggest")
async def suggest(q: str = ""):
    q = q.strip()
    if len(q) < 1:
        return []
    db = await open_db()
    try:
        cur = await db.execute(
            "SELECT name, category FROM item_history "
            "WHERE name LIKE ? COLLATE NOCASE ORDER BY use_count DESC, name LIMIT 8",
            (q + "%",),
        )
        return [dict(r) for r in await cur.fetchall()]
    finally:
        await db.close()
