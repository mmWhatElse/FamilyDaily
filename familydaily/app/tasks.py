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


class SeriesPatch(BaseModel):
    title: str | None = None
    person_ids: list[int] | None = None
    recurrence: str | None = None
    start_date: str | None = None
    active: bool | None = None


def _current_due(recurrence: str, param: int, today: date, start_date: date | None = None) -> date:
    """The due date of the current period's instance."""
    if recurrence == "daily":
        return max(today, start_date) if start_date else today
    if recurrence == "weekly":
        # param = weekday (0=Montag); this week's occurrence
        monday = today - timedelta(days=today.weekday())
        due = monday + timedelta(days=param)
        return start_date if start_date and start_date > due else due
    if recurrence == "monthly":
        last = cal.monthrange(today.year, today.month)[1]
        due = today.replace(day=min(param, last))
        return start_date if start_date and start_date > due else due
    return today


def _next_due(recurrence: str, param: int, today: date, start_date: date | None = None) -> date:
    due = _current_due(recurrence, param, today, start_date)
    if due >= today:
        return due
    if recurrence == "weekly":
        return due + timedelta(days=7)
    if recurrence == "monthly":
        year, month = today.year, today.month + 1
        if month == 13:
            year, month = year + 1, 1
        last = cal.monthrange(year, month)[1]
        return date(year, month, min(param, last))
    return today


async def _materialize(db, target: date | None = None) -> None:
    """Ensure each active template has its current-period instance."""
    today = target or date.today()
    cur = await db.execute("SELECT * FROM task_template WHERE active = 1")
    for tpl in await cur.fetchall():
        start = date.fromisoformat(tpl["start_date"]) if tpl["start_date"] else None
        due = _current_due(tpl["recurrence"], tpl["recurrence_param"] or 0, today, start)
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


def _series_row(r, today: date | None = None) -> dict:
    d = dict(r)
    d["person_ids"] = json.loads(d["person_ids"] or "[]")
    d["active"] = bool(d["active"])
    if d["active"]:
        start = date.fromisoformat(d["start_date"]) if d["start_date"] else None
        d["next_due"] = _next_due(
            d["recurrence"], d["recurrence_param"] or 0, today or date.today(), start
        ).isoformat()
    else:
        d["next_due"] = None
    return d


@router.get("/series")
async def get_series():
    db = await open_db()
    try:
        cur = await db.execute("SELECT * FROM task_template ORDER BY active DESC, title, id")
        return [_series_row(r) for r in await cur.fetchall()]
    finally:
        await db.close()


@router.patch("/series/{series_id}")
async def patch_series(series_id: int, data: SeriesPatch):
    db = await open_db()
    try:
        row = await (await db.execute(
            "SELECT * FROM task_template WHERE id = ?", (series_id,)
        )).fetchone()
        if not row:
            raise HTTPException(404, "Wiederholung nicht gefunden")
        values = dict(row)
        if data.title is not None:
            title = data.title.strip()
            if not title:
                raise HTTPException(422, "Titel darf nicht leer sein")
            values["title"] = title
        if data.person_ids is not None:
            values["person_ids"] = json.dumps(data.person_ids)
        if data.recurrence is not None:
            if data.recurrence not in RECURRENCES or data.recurrence == "none":
                raise HTTPException(422, "Ungültige Wiederholung")
            values["recurrence"] = data.recurrence
        if data.start_date is not None:
            date.fromisoformat(data.start_date)
            values["start_date"] = data.start_date
        base = date.fromisoformat(values["start_date"]) if values["start_date"] else date.today()
        values["recurrence_param"] = base.weekday() if values["recurrence"] == "weekly" else base.day
        if data.active is not None:
            values["active"] = int(data.active)
        await db.execute(
            "UPDATE task_template SET title=?, person_ids=?, recurrence=?, recurrence_param=?, "
            "start_date=?, active=? WHERE id=?",
            (values["title"], values["person_ids"], values["recurrence"],
             values["recurrence_param"], values["start_date"], values["active"], series_id),
        )
        if data.title is not None or data.person_ids is not None:
            await db.execute(
                "UPDATE task SET title=?, person_ids=? WHERE template_id=? AND done=0 AND skipped=0",
                (values["title"], values["person_ids"], series_id),
            )
        if data.recurrence is not None or data.start_date is not None:
            await db.execute(
                "DELETE FROM task WHERE template_id=? AND done=0 AND skipped=0 AND due_date>=?",
                (series_id, date.today().isoformat()),
            )
            if values["active"]:
                await _materialize(db)
        await db.commit()
        await broadcaster.broadcast({"type": "tasks"})
        return {"ok": True}
    finally:
        await db.close()


@router.delete("/series/{series_id}", status_code=204)
async def delete_series(series_id: int):
    db = await open_db()
    try:
        await db.execute("DELETE FROM task WHERE template_id = ?", (series_id,))
        cur = await db.execute("DELETE FROM task_template WHERE id = ?", (series_id,))
        if cur.rowcount == 0:
            raise HTTPException(404, "Wiederholung nicht gefunden")
        await db.commit()
        await broadcaster.broadcast({"type": "tasks"})
    finally:
        await db.close()


@router.get("/preview")
async def preview_tasks(target: str):
    target_date = date.fromisoformat(target)
    db = await open_db()
    try:
        await _materialize(db, target_date)
        cur = await db.execute(
            "SELECT task.*, task_template.recurrence AS recurrence "
            "FROM task LEFT JOIN task_template ON task.template_id = task_template.id "
            "WHERE task.skipped = 0 AND task.done = 0 AND task.due_date = ? ORDER BY id",
            (target_date.isoformat(),),
        )
        return [_row(r) for r in await cur.fetchall()]
    finally:
        await db.close()


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
                "INSERT INTO task_template (title, person_ids, recurrence, recurrence_param, start_date) "
                "VALUES (?, ?, ?, ?, ?)",
                (title, person_ids, data.recurrence, param, base.isoformat()),
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
