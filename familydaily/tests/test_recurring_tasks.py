import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
