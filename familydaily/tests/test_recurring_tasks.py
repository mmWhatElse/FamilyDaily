import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

import aiosqlite

from app import db as db_module
from app import tasks


class RecurringTaskDeleteTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_module.DATA_DIR = Path(self.temp_dir.name)
        db_module.DB_PATH = db_module.DATA_DIR / "familydaily.db"
        await db_module.init_db()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def _create_daily_task(self):
        await tasks.create_task(tasks.TaskIn(title="Täglich", recurrence="daily"))
        rows = await tasks.get_tasks()
        return next(row for row in rows if row["title"] == "Täglich")

    def test_next_weekly_due_moves_past_weekday_to_next_week(self):
        saturday = date(2026, 7, 11)
        self.assertEqual(
            tasks._next_due("weekly", 4, saturday),
            date(2026, 7, 17),
        )

    async def test_deleting_one_occurrence_does_not_materialize_it_again(self):
        task = await self._create_daily_task()

        await tasks.delete_task(task["id"], series=False)

        self.assertEqual(await tasks.get_tasks(), [])
        db = await db_module.open_db()
        try:
            row = await (await db.execute(
                "SELECT skipped FROM task WHERE id = ?", (task["id"],)
            )).fetchone()
            self.assertEqual(row["skipped"], 1)
        finally:
            await db.close()

    async def test_deleting_series_removes_template_and_all_occurrences(self):
        task = await self._create_daily_task()
        template_id = task["template_id"]

        await tasks.delete_task(task["id"], series=True)

        self.assertEqual(await tasks.get_tasks(), [])
        db = await db_module.open_db()
        try:
            template = await (await db.execute(
                "SELECT id FROM task_template WHERE id = ?", (template_id,)
            )).fetchone()
            linked = await (await db.execute(
                "SELECT COUNT(*) FROM task WHERE template_id = ?", (template_id,)
            )).fetchone()
            self.assertIsNone(template)
            self.assertEqual(linked[0], 0)
        finally:
            await db.close()

    async def test_series_can_be_paused_edited_and_resumed(self):
        task = await self._create_daily_task()
        series_id = task["template_id"]

        await tasks.patch_series(series_id, tasks.SeriesPatch(active=False, title="Neue Routine"))
        series = await tasks.get_series()
        self.assertFalse(series[0]["active"])
        self.assertEqual(series[0]["title"], "Neue Routine")
        self.assertIsNone(series[0]["next_due"])
        current = await tasks.get_tasks()
        self.assertEqual(current[0]["title"], "Neue Routine")

        tomorrow = (date.today() + timedelta(days=1)).isoformat()
        await tasks.patch_series(
            series_id, tasks.SeriesPatch(active=True, recurrence="weekly", start_date=tomorrow)
        )
        series = await tasks.get_series()
        self.assertTrue(series[0]["active"])
        self.assertEqual(series[0]["recurrence"], "weekly")
        self.assertEqual(series[0]["next_due"], tomorrow)

    async def test_tomorrow_preview_materializes_daily_series(self):
        await self._create_daily_task()
        tomorrow = (date.today() + timedelta(days=1)).isoformat()

        preview = await tasks.preview_tasks(tomorrow)

        self.assertEqual(len(preview), 1)
        self.assertEqual(preview[0]["due_date"], tomorrow)

    async def test_legacy_series_gets_start_date_during_migration(self):
        db_module.DB_PATH.unlink()
        async with aiosqlite.connect(db_module.DB_PATH) as legacy:
            await legacy.executescript("""
                CREATE TABLE task_template (
                    id INTEGER PRIMARY KEY, title TEXT NOT NULL, person_ids TEXT NOT NULL DEFAULT '[]',
                    recurrence TEXT NOT NULL DEFAULT 'none', recurrence_param INTEGER,
                    active INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE task (
                    id INTEGER PRIMARY KEY, template_id INTEGER, title TEXT NOT NULL,
                    person_ids TEXT NOT NULL DEFAULT '[]', due_date TEXT, done INTEGER NOT NULL DEFAULT 0,
                    completed_at TEXT, skipped INTEGER NOT NULL DEFAULT 0
                );
                INSERT INTO task_template (id, title, recurrence, recurrence_param)
                VALUES (1, 'Altserie', 'weekly', 2);
                INSERT INTO task (template_id, title, due_date) VALUES (1, 'Altserie', '2026-07-08');
            """)
            await legacy.commit()

        await db_module.init_db()

        db = await db_module.open_db()
        try:
            row = await (await db.execute(
                "SELECT start_date FROM task_template WHERE id = 1"
            )).fetchone()
            self.assertEqual(row["start_date"], "2026-07-08")
        finally:
            await db.close()


if __name__ == "__main__":
    unittest.main()
