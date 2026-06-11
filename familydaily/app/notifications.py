"""Benachrichtigungen — HA notify-Integration mit Hintergrund-Scheduler."""

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .db import open_db
from .ha import HAError, ha_get, ha_post

router = APIRouter(prefix="/api/notifications", tags=["notifications"])
log = logging.getLogger(__name__)


class NotificationSettings(BaseModel):
    enabled: bool = False
    notify_services: list[str] = []
    task_reminder_time: str = "08:00"   # HH:MM (local time)
    event_lead_minutes: int = 30


def _row_services(row) -> list[str]:
    """Service-Liste aus der Zeile; fällt aufs alte Einzelfeld zurück."""
    try:
        services = json.loads(row["notify_services"] or "[]")
    except (ValueError, TypeError):
        services = []
    if not services and row["notify_service"]:
        services = [row["notify_service"]]
    return services


# ─── API endpoints ────────────────────────────────────────────────────────────

@router.get("/settings")
async def get_settings():
    db = await open_db()
    try:
        cur = await db.execute("SELECT * FROM notification_settings WHERE id = 1")
        row = await cur.fetchone()
        if not row:
            return NotificationSettings().model_dump()
        return {
            "enabled": bool(row["enabled"]),
            "notify_services": _row_services(row),
            "task_reminder_time": row["task_reminder_time"],
            "event_lead_minutes": row["event_lead_minutes"],
        }
    finally:
        await db.close()


@router.put("/settings")
async def put_settings(data: NotificationSettings):
    db = await open_db()
    try:
        await db.execute(
            "INSERT INTO notification_settings "
            "(id, enabled, notify_service, notify_services, task_reminder_time, event_lead_minutes) "
            "VALUES (1, ?, ?, ?, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET "
            "  enabled=excluded.enabled, "
            "  notify_service=excluded.notify_service, "
            "  notify_services=excluded.notify_services, "
            "  task_reminder_time=excluded.task_reminder_time, "
            "  event_lead_minutes=excluded.event_lead_minutes",
            (int(data.enabled),
             data.notify_services[0] if data.notify_services else "",
             json.dumps(data.notify_services),
             data.task_reminder_time, data.event_lead_minutes),
        )
        await db.commit()
        return {"ok": True}
    finally:
        await db.close()


@router.get("/services")
async def list_notify_services():
    """List HA notify services available for push notifications."""
    try:
        services_list = await ha_get("/services")
    except (HAError, Exception) as exc:
        return {"error": str(exc), "services": []}
    notify = next((s for s in services_list if s.get("domain") == "notify"), None)
    if not notify:
        return {"services": []}
    return {"services": [f"notify.{k}" for k in notify.get("services", {}).keys()]}


@router.post("/test")
async def send_test():
    """Immediately send a test notification to verify the configured service."""
    db = await open_db()
    try:
        cur = await db.execute("SELECT * FROM notification_settings WHERE id = 1")
        row = await cur.fetchone()
    finally:
        await db.close()
    services = _row_services(row) if row else []
    if not services:
        raise HTTPException(400, "Kein Notify-Service konfiguriert")
    try:
        await _send_all(services,
                        title="FamilyDaily ✓",
                        message="Testbenachrichtigung erfolgreich empfangen.")
    except (HAError, Exception) as exc:
        raise HTTPException(502, f"Benachrichtigung fehlgeschlagen: {exc}")
    return {"ok": True}


# ─── Internal helpers ─────────────────────────────────────────────────────────

async def _send(service: str, *, title: str, message: str) -> None:
    """Call HA notify service. service = 'notify.mobile_app_xyz'."""
    parts = service.split(".", 1)
    if len(parts) != 2:
        raise HAError(f"Ungültiger Service-Name: {service!r}")
    domain, svc = parts
    await ha_post(f"/services/{domain}/{svc}", {"title": title, "message": message})


async def _send_all(services: list[str], *, title: str, message: str) -> None:
    """An alle konfigurierten Services senden; erst am Ende scheitern, falls alle scheitern."""
    errors = []
    for service in services:
        try:
            await _send(service, title=title, message=message)
        except (HAError, Exception) as exc:
            log.warning("Senden an %s fehlgeschlagen: %s", service, exc)
            errors.append(exc)
    if errors and len(errors) == len(services):
        raise errors[0]


async def _already_sent(db, key: str) -> bool:
    cur = await db.execute("SELECT key FROM notification_sent WHERE key = ?", (key,))
    return await cur.fetchone() is not None


async def _mark_sent(db, key: str) -> None:
    await db.execute(
        "INSERT OR IGNORE INTO notification_sent (key, sent_at) VALUES (?, ?)",
        (key, datetime.now(timezone.utc).isoformat()),
    )
    await db.commit()


# ─── Reminder logic ───────────────────────────────────────────────────────────

async def _task_reminders(db, settings: dict) -> None:
    """At the configured time, send a summary of tasks due today."""
    now = datetime.now()
    target_h, target_m = map(int, settings["task_reminder_time"].split(":"))
    if not (now.hour == target_h and now.minute == target_m):
        return

    today = date.today().isoformat()
    key = f"task_due_{today}"
    if await _already_sent(db, key):
        return

    cur = await db.execute(
        "SELECT title FROM task WHERE done = 0 AND due_date IS NOT NULL AND due_date <= ? "
        "ORDER BY due_date, id",
        (today,),
    )
    rows = await cur.fetchall()
    if not rows:
        return

    count = len(rows)
    preview = ", ".join(r["title"] for r in rows[:3])
    if count > 3:
        preview += f" (+{count - 3} weitere)"

    await _send_all(
        settings["notify_services"],
        title=f"FamilyDaily — {count} Aufgabe{'n' if count != 1 else ''} heute",
        message=preview,
    )
    await _mark_sent(db, key)


async def _event_reminders(db, settings: dict) -> None:
    """Send a reminder for each upcoming calendar event within the lead window."""
    lead = settings["event_lead_minutes"]
    now_utc = datetime.now(timezone.utc)
    window_end = now_utc + timedelta(minutes=lead + 1)

    cur = await db.execute("SELECT entity_id FROM calendar_settings WHERE enabled = 1")
    entities = [r["entity_id"] for r in await cur.fetchall()]
    if not entities:
        return

    fmt = "%Y-%m-%dT%H:%M:%SZ"
    start_str = now_utc.strftime(fmt)
    end_str = window_end.strftime(fmt)

    for entity_id in entities:
        try:
            events = await ha_get(
                f"/calendars/{entity_id}",
                params={"start": start_str, "end": end_str},
            )
        except Exception:
            continue

        for ev in events:
            ev_start_obj = ev.get("start") or {}
            if "dateTime" not in ev_start_obj:
                continue  # all-day event — skip
            ev_start_raw = ev_start_obj["dateTime"]
            uid = ev.get("uid") or ev.get("summary", "unknown")
            key = f"event_{entity_id}_{uid}_{ev_start_raw[:16]}"
            if await _already_sent(db, key):
                continue

            try:
                ev_dt = datetime.fromisoformat(ev_start_raw)
                if ev_dt.tzinfo is None:
                    ev_dt = ev_dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue

            diff = int((ev_dt - now_utc).total_seconds() / 60)
            if diff < 0 or diff > lead:
                continue

            time_str = ev_dt.astimezone().strftime("%H:%M")
            summary = ev.get("summary", "Termin")
            await _send_all(
                settings["notify_services"],
                title=f"FamilyDaily — {summary}",
                message=f"Beginnt um {time_str} (in {diff} Min.)",
            )
            await _mark_sent(db, key)


# ─── Background loop ──────────────────────────────────────────────────────────

async def check_and_send() -> None:
    """Single check pass — called once per minute from the loop."""
    db = await open_db()
    try:
        cur = await db.execute("SELECT * FROM notification_settings WHERE id = 1")
        row = await cur.fetchone()
        if not row or not row["enabled"]:
            return
        services = _row_services(row)
        if not services:
            return
        settings = {**dict(row), "notify_services": services}
        await _task_reminders(db, settings)
        await _event_reminders(db, settings)
        # Purge dedup entries older than 3 days
        cutoff = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        await db.execute("DELETE FROM notification_sent WHERE sent_at < ?", (cutoff,))
        await db.commit()
    except Exception:
        log.exception("Fehler im Benachrichtigungs-Check")
    finally:
        await db.close()


async def notification_loop() -> None:
    """Runs forever; fires once per minute aligned to minute boundaries."""
    while True:
        now = datetime.now()
        # Sleep until the next full minute
        sleep_secs = 60 - now.second - now.microsecond / 1_000_000
        await asyncio.sleep(max(sleep_secs, 1))
        await check_and_send()
