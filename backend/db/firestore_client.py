from google.cloud import firestore
from backend.config import PROJECT_ID, FIRESTORE_DATABASE
from datetime import datetime, timezone

db = firestore.AsyncClient(project=PROJECT_ID, database=FIRESTORE_DATABASE)


async def save_recipe(recipe: dict) -> None:
    """
    Saves a recipe to Firestore recipes collection.
    Uses Spoonacular ID as the document ID so we never duplicate.
    """
    recipe_id = str(recipe["id"])

    # Add timestamp so we know when it was cached
    recipe["cached_at"] = datetime.now(timezone.utc)

    await db.collection("recipes").document(recipe_id).set(recipe)
    print(f"  ✓ Saved recipe to Firestore: {recipe['name']} (id: {recipe_id})")


async def get_recipe_by_id(recipe_id: str) -> dict | None:
    """
    Fetch a single recipe by Spoonacular ID.
    Returns None if not found.
    """
    doc = await db.collection("recipes").document(recipe_id).get()

    if doc.exists:
        return doc.to_dict()

    return None


async def recipe_exists(recipe_id: str) -> bool:
    """
    Check if a recipe is already cached before saving.
    Avoids overwriting with less complete data.
    """
    doc = await db.collection("recipes").document(recipe_id).get()
    return doc.exists


async def get_all_recipes() -> list:
    """
    Returns all cached recipes.
    Used for browsing before a user has searched anything.
    """
    docs = db.collection("recipes").stream()
    recipes = []
    async for doc in docs:
        recipes.append(doc.to_dict())
    return recipes


async def search_recipes_by_name(query: str) -> list:
    """
    Basic name search in Firestore.
    Not a replacement for Spoonacular — used for quick lookups
    of already-cached recipes only.
    """
    docs = db.collection("recipes").stream()
    results = []
    query_lower = query.lower()

    async for doc in docs:
        data = doc.to_dict()
        if query_lower in data.get("name", "").lower():
            results.append(data)

    return results
