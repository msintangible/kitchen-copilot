from google.cloud import firestore
from backend/config.py import PROJECT_ID, FIRESTORE_DATABASE

db = firestore.AsyncClient(project=PROJECT_ID, database=FIRESTORE_DATABASE)

async def get_recipe_by_id(recipe_id: str) -> dict:
#TODO
pass

async def search_recipes(query: str) -> list:
#TODO
pass

async def get_all_recipes() -> list:
#TODO
pass

