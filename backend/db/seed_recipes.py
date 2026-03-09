import asyncio

from google.cloud import firestore
from backend.config import PROJECT_ID, FIRESTORE_DATABASE

db = firestore.AsyncClient(project=PROJECT_ID, database=FIRESTORE_DATABASE)

RECIPES = [
      # TODO: Day 4 - Add 10-20 curated recipes following the Firestore schema
      # Each recipe must include:
      # - name, description, cuisine, difficulty, prep_time_minutes, cook_time_minutes, servings
      # - dietary_tags: list of strings
      # - ingredients: list of {name, quantity, unit, category, essential}
      # - steps: list of {order, instruction, duration_minutes, requires_timer, visual_cue}
      # - tips: list of strings
      # - common_mistakes: list of strings
  ]
async def seed():
      collection = db.collection("recipes")
      for recipe in RECIPES:
          await collection.add(recipe)
          print(f"Seeded recipe: {recipe['name']}")

if __name__ == "__main__":
      		asyncio.run(seed())
