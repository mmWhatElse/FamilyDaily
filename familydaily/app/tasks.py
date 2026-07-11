"""Aufgaben — tasks API with recurrence (template + materialized instances)."""

import calendar as cal
import json
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ws import broadcaster

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

RECURRENCES = ("none", "daily", "weekly", "monthly")


class TaskIn(BaseModel):
    title: str
    person_ids: list[int] = []
    due_date: str | None = None  # ISO date
    recurrence: str = "none"


class TaskPatch(BaseModel):
    title: str | None = None
    person_ids: list[int] | None = None
    due_date: str | None = None
    done: bool | None = None


def _current_due(recurrence: str, param: int, today: date) -> date:
    """The due date of the current period's instance."""
    if recurrence == "daily":
        return today
    if recurrence == "weekly":
        # param = weekday (0=Montag); this week's occurrence
        monday = today - timedelta(days=today.weekday())
        return monday + timedelta(days=param)
    if recurrence == "monthly":
        last = cal.monthrange(today.year, today.month)[1]
        return today.replace(day=min(param, last))
    return today


async def _materialize(db) -> None:
    """Ensure each active template has its current-period instance."""
    today = date.today()
    cur = await db.execute("SELECT * FROM task_template WHERE active = 1")
    for tpl in await cur.fetchall():
        due = _current_due(tpl["recurrence"], tpl["recurrence_param"] or 0, today)
        if due > today:
            continue  # this period's occurrence hasn't arrived yet
        cur2 = await db.execute(
            "SELECT id FROM task WHERE template_id = ? AND due_date = ?",
            (tpl["id"], due.isoformat()),
        )
        if not await cur2.fetchone():
            await db.execute(
                "INSERT INTO task (template_id, title, person_ids, due_date) VALUES (?, ?, ?, ?)",
                (tpl["id"], tpl["title"], tpl["person_ids"], due.isoformat()),
            )
    await db.commit()


def _row(r) -> dict:
    d = dict(r)
    d["person_ids"] = json.loads(d["person_ids"] or "[]")
    d["done"] = bool(d["done"])
    return d


@router.get("")
async def get_tasks(view: str = "open"):
    """view=open: all open + recently completed. view=today: due today or overdue."""
    db = await open_db()
    try:
        await _materialize(db)
        if view == "today":
            cur = await db.execute(
                "SELECT task.*, task_template.recurrence AS recurrence "
                "FROM task LEFT JOIN task_template ON task.template_id = task_template.id "
                "WHERE task.skipped = 0 AND task.done = 0 "
                "AND task.due_date IS NOT NULL AND task.due_date <= ? "
                "ORDER BY due_date, id",
                (date.today().isoformat(),),
            )
        else:
            cutoff = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
            cur = await db.execute(
                "SELECT task.*, task_template.recurrence AS recurrence "
                "FROM task LEFT JOIN task_template ON task.template_id = task_template.id "
                "WHERE task.skipped = 0 AND (task.done = 0 OR task.completed_at > ?) "
                "ORDER BY task.done, task.due_date IS NULL, task.due_date, task.id",
                (cutoff,),
            )
        return [_row(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.post("", status_code=201)
async def create_task(data: TaskIn):
    title = data.title.strip()
    if not title:
        raise HTTPException(422, "Titel darf nicht leer sein")
    if data.recurrence not in RECURRENCES:
        raise HTTPException(422, "Ungültige Wiederholung")
    person_ids = json.dumps(data.person_ids)
    db = await open_db()
    try:
        if data.recurrence == "none":
            cur = await db.execute(
                "INSERT INTO task (title, person_ids, due_date) VALUES (?, ?, ?)",
                (title, person_ids, data.due_date),
            )
            await db.commit()
            new_id = cur.lastrowid
        else:
            base = date.fromisoformat(data.due_date) if data.due_date else date.today()
            param = base.weekday() if data.recurrence == "weekly" else base.day
            cur = await db.execute(
                "INSERT INTO task_template (title, person_ids, recurrence, recurrence_param) "
                "VALUES (?, ?, ?, ?)",
                (title, person_ids, data.recurrence, param),
            )
            await db.commit()
            await _materialize(db)
            new_id = cur.lastrowid
        await broadcaster.broadcast({"type": "tasks"})
        return {"id": new_id}
    finally:
        await db.close()


@router.patch("/{task_id}")
async def patch_task(task_id: int, data: TaskPatch):
    db = await open_db()
    try:
        cur = await db.execute("SELECT id FROM task WHERE id = ?", (task_id,))
        if not await cur.fetchone():
            raise HTTPException(404, "Aufgabe nicht gefunden")
        if data.title is not None:
            title = data.title.strip()
            if not title:
                raise HTTPException(422, "Titel darf nicht leer sein")
            await db.execute("UPDATE task SET title = ? WHERE id = ?", (title, task_id))
        if data.person_ids is not None:
            await db.execute(
                "UPDATE task SET person_ids = ? WHERE id = ?",
                (json.dumps(data.person_ids), task_id),
            )
        if "due_date" in data.model_fields_set:
            await db.execute("UPDATE task SET due_date = ? WHERE id = ?", (data.due_date, task_id))
        if data.done is not None:
            completed = datetime.now(timezone.utc).isoformat() if data.done else None
            await db.execute(
                "UPDATE task SET done = ?, completed_at = ? WHERE id = ?",
                (int(data.done), completed, task_id),
            )
        await db.commit()
        await broadcaster.broadcast({"type": "tasks"})
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: int, series: bool = False):
    """Delete one occurrence, or permanently remove its complete recurring series."""
    db = await open_db()
    try:
        cur = await db.execute("SELECT template_id FROM task WHERE id = ?", (task_id,))
        row = await cur.fetchone()
        if not row:
            raise HTTPException(404, "Aufgabe nicht gefunden")
        template_id = row["template_id"]
        if template_id and series:
            await db.execute("DELETE FROM task WHERE template_id = ?", (template_id,))
            await db.execute("DELETE FROM task_template WHERE id = ?", (template_id,))
        elif template_id:
            # Die Zeile bleibt als Tombstone erhalten. _materialize erkennt dadurch,
            # dass dieses Vorkommen bereits behandelt wurde, während die UI es ausblendet.
            await db.execute("UPDATE task SET skipped = 1 WHERE id = ?", (task_id,))
        else:
            await db.execute("DELETE FROM task WHERE id = ?", (task_id,))
        await db.commit()
        await broadcaster.broadcast({"type": "tasks"})
    finally:
        await db.close()
