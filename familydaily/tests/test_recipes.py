import tempfile
import unittest
from datetime import date
from pathlib import Path

import aiosqlite

from app import db as db_module
from app import meals, recipes, shopping


class RecipeAndMealPlanTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_module.DATA_DIR = Path(self.temp_dir.name)
        db_module.DB_PATH = db_module.DATA_DIR / "familydaily.db"
        await db_module.init_db()

    async def asyncTearDown(self):
        self.temp_dir.cleanup()

    async def test_starter_recipes_cover_all_categories(self):
        items = await recipes.get_recipes()
        self.assertGreaterEqual(len(items), 20)
        self.assertEqual(
            {item["category"] for item in items},
            {"breakfast", "main", "snack"},
        )
        self.assertTrue(all(item["ingredients"] for item in items))
        self.assertTrue(any(item["tags"] for item in items))

    async def test_recipe_can_be_created_and_edited(self):
        created = await recipes.create_recipe(recipes.RecipeIn(
            name="Familien-Porridge",
            category="breakfast",
            calories=410,
            protein=25,
            ingredients=["50 g Haferflocken", "250 ml Milch"],
        ))
        updated = await recipes.update_recipe(created["id"], recipes.RecipeIn(
            name="Familien-Porridge mit Apfel",
            category="breakfast",
            calories=440,
            protein=26,
            ingredients=["50 g Haferflocken", "250 ml Milch", "1 Apfel"],
            tags=["quick", "family"],
        ))
        self.assertEqual(updated["calories"], 440)
        self.assertIn("1 Apfel", updated["ingredients"])
        self.assertEqual(updated["tags"], ["quick", "family"])

    async def test_favorite_and_last_cooked_are_derived_for_recipe_box(self):
        recipe = await recipes.create_recipe(recipes.RecipeIn(
            name="Lieblingsgericht", category="main", calories=500,
            ingredients=["1 Lieblingszutat"], tags=["family"],
        ))
        await recipes.set_favorite(recipe["id"], recipes.FavoriteIn(favorite=True))
        today = date.today().isoformat()
        await meals.set_meal(today, meals.MealIn(
            title=recipe["name"], category="dinner", ingredients=recipe["ingredients"],
            calories=recipe["calories"], recipe_id=recipe["id"],
        ))

        found = (await recipes.get_recipes(q="Lieblingsgericht"))[0]

        self.assertTrue(found["favorite"])
        self.assertEqual(found["last_cooked"], today)
        self.assertEqual(found["tags"], ["family"])

    async def test_old_lunch_and_dinner_recipes_become_main_dishes(self):
        db = await db_module.open_db()
        try:
            await db.execute("UPDATE recipe SET category = 'dinner' WHERE id = 1")
            await db.execute("UPDATE recipe SET category = 'lunch' WHERE id = 2")
            await db.commit()
        finally:
            await db.close()

        await db_module.init_db()

        db = await db_module.open_db()
        try:
            rows = await (await db.execute(
                "SELECT category FROM recipe WHERE id IN (1, 2) ORDER BY id"
            )).fetchall()
            self.assertEqual([row["category"] for row in rows], ["main", "main"])
        finally:
            await db.close()

    async def test_deleting_recipe_keeps_planned_meal_snapshot(self):
        recipe = await recipes.create_recipe(recipes.RecipeIn(
            name="Testgericht",
            category="main",
            calories=500,
            ingredients=["200 g Testzutat"],
        ))
        day = "2026-07-20"
        await meals.set_meal(day, meals.MealIn(
            title=recipe["name"], category="dinner", calories=recipe["calories"],
            ingredients=recipe["ingredients"], recipe_id=recipe["id"],
        ))

        await recipes.delete_recipe(recipe["id"])

        self.assertEqual(await recipes.get_recipes(q="Testgericht"), [])
        planned = (await meals.get_meals(day, day))[0]
        self.assertEqual(planned["title"], "Testgericht")
        self.assertEqual(planned["ingredients"], ["200 g Testzutat"])
        self.assertIsNone(planned["recipe_id"])

    async def test_four_categories_can_share_one_day(self):
        day = "2026-07-15"
        for category in ("breakfast", "lunch", "dinner", "snack"):
            await meals.set_meal(day, meals.MealIn(
                title=category.title(), category=category,
                calories=400, ingredients=["1 Testzutat"],
            ))
        planned = await meals.get_meals(day, day)
        self.assertEqual(len(planned), 4)
        self.assertEqual({item["category"] for item in planned},
                         {"breakfast", "lunch", "dinner", "snack"})

    async def test_bulk_shopping_add_is_idempotent(self):
        list_id = (await shopping.get_lists())[0]["id"]
        first = await shopping.add_items_bulk(
            list_id, shopping.ItemBulkIn(names=["250 g Skyr", "150 g Beeren"])
        )
        second = await shopping.add_items_bulk(
            list_id, shopping.ItemBulkIn(names=["250 g Skyr", "150 g Beeren"])
        )
        self.assertEqual(first["added"], 2)
        self.assertEqual(second["added"], 0)

    async def test_legacy_dinner_is_preserved_during_migration(self):
        db_module.DB_PATH.unlink()
        async with aiosqlite.connect(db_module.DB_PATH) as legacy:
            await legacy.executescript("""
                CREATE TABLE meal (
                    id INTEGER PRIMARY KEY, date TEXT NOT NULL UNIQUE,
                    title TEXT NOT NULL, note TEXT, url TEXT, ingredients TEXT
                );
                INSERT INTO meal (date, title, ingredients)
                VALUES ('2026-07-15', 'Altes Abendessen', '["Kartoffeln"]');
            """)
            await legacy.commit()

        await db_module.init_db()

        planned = await meals.get_meals("2026-07-15", "2026-07-15")
        self.assertEqual(planned[0]["title"], "Altes Abendessen")
        self.assertEqual(planned[0]["category"], "dinner")


if __name__ == "__main__":
    unittest.main()
