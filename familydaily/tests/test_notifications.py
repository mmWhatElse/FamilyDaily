import json
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import aiosqlite

from app import db as db_module
from app import notifications, persons


class PersonNotificationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_module.DATA_DIR = Path(self.temp_dir.name)
        db_module.DB_PATH = db_module.DATA_DIR / "familydaily.db"
        await db_module.init_db()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_person_devices_are_stored_and_returned_as_a_list(self):
        created = await persons.create_person(persons.PersonIn(
            name="Bianca",
            notify_services=["notify.mobile_app_iphone_von_bianca"],
        ))

        found = next(p for p in await persons.get_persons() if p["id"] == created["id"])

        self.assertEqual(
            found["notify_services"],
            ["notify.mobile_app_iphone_von_bianca"],
        )

    async def test_existing_persons_are_preserved_by_device_migration(self):
        db_module.DB_PATH.unlink()
        async with aiosqlite.connect(db_module.DB_PATH) as legacy:
            await legacy.execute("""CREATE TABLE person (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                color TEXT NOT NULL DEFAULT '#4a90d9',
                emoji TEXT,
                calendar_entity_id TEXT
            )""")
            await legacy.execute("INSERT INTO person (name) VALUES ('Bianca')")
            await legacy.commit()

        await db_module.init_db()

        found = (await persons.get_persons())[0]
        self.assertEqual(found["name"], "Bianca")
        self.assertEqual(found["notify_services"], [])

    async def test_task_reminders_are_grouped_by_person_device(self):
        db = await db_module.open_db()
        try:
            await db.executemany(
                "INSERT INTO person (name, notify_services) VALUES (?, ?)",
                [
                    ("Bianca", json.dumps(["notify.iphone_bianca", "notify.shared"])),
                    ("Mathias", json.dumps(["notify.iphone_mathias", "notify.shared"])),
                ],
            )
            today = date.today().isoformat()
            await db.executemany(
                "INSERT INTO task (title, person_ids, due_date) VALUES (?, ?, ?)",
                [
                    ("Nur Bianca", "[1]", today),
                    ("Gemeinsam", "[1, 2]", today),
                    ("Ohne Person", "[]", today),
                ],
            )
            await db.commit()

            settings = {
                "task_reminder_time": datetime.now().strftime("%H:%M"),
                "notify_services": ["notify.standard"],
            }
            with patch.object(notifications, "_send_all", new=AsyncMock()) as send:
                await notifications._task_reminders(db, settings)

            calls_by_service = {
                call.args[0][0]: call.kwargs["message"]
                for call in send.await_args_list
            }
            self.assertEqual(set(calls_by_service), {
                "notify.iphone_bianca", "notify.iphone_mathias",
                "notify.shared", "notify.standard",
            })
            self.assertIn("Nur Bianca", calls_by_service["notify.iphone_bianca"])
            self.assertIn("Gemeinsam", calls_by_service["notify.iphone_bianca"])
            self.assertEqual(calls_by_service["notify.iphone_mathias"], "Gemeinsam")
            self.assertEqual(calls_by_service["notify.standard"], "Ohne Person")
            self.assertIn("Gemeinsam", calls_by_service["notify.shared"])
            self.assertEqual(send.await_count, 4)
        finally:
            await db.close()

    async def test_event_reminder_goes_to_all_tagged_persons_but_not_standard(self):
        db = await db_module.open_db()
        try:
            await db.executemany(
                "INSERT INTO person (name, notify_services) VALUES (?, ?)",
                [
                    ("Bianca", '["notify.iphone_bianca", "notify.shared"]'),
                    ("Mathias", '["notify.iphone_mathias", "notify.shared"]'),
                ],
            )
            await db.execute(
                "INSERT INTO calendar_settings (entity_id) VALUES (?)",
                ("calendar.family",),
            )
            await db.commit()
            event_start = (datetime.now(timezone.utc) + timedelta(minutes=5)).isoformat()
            events = [{
                "uid": "family-event",
                "summary": "Gemeinsamer Termin",
                "start": {"dateTime": event_start},
                "description": "Details\n<!--fd-persons:1,2-->",
            }]
            with (
                patch.object(notifications, "ha_get", new=AsyncMock(return_value=events)),
                patch.object(notifications, "_send_all", new=AsyncMock()) as send,
            ):
                await notifications._event_reminders(db, {
                    "event_lead_minutes": 30,
                    "notify_services": ["notify.standard"],
                })

            called_services = [call.args[0][0] for call in send.await_args_list]
            self.assertEqual(set(called_services), {
                "notify.iphone_bianca", "notify.iphone_mathias", "notify.shared",
            })
            self.assertNotIn("notify.standard", called_services)
            self.assertEqual(called_services.count("notify.shared"), 1)
        finally:
            await db.close()

    def test_assigned_entries_do_not_fall_back_to_standard_devices(self):
        self.assertEqual(
            notifications._services_for_persons([1], {1: []}, ["notify.standard"]),
            [],
        )
        self.assertEqual(
            notifications._services_for_persons([], {}, ["notify.standard"]),
            ["notify.standard"],
        )


if __name__ == "__main__":
    unittest.main()
