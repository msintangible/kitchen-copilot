from google.cloud import firestore
from config import PROJECT_ID, FIRESTORE_DATABASE
from datetime import datetime, timezone
import hashlib

try:
    from google.auth.exceptions import DefaultCredentialsError
    db = firestore.AsyncClient(project=PROJECT_ID, database=FIRESTORE_DATABASE)
except DefaultCredentialsError:
    print("  ! Google Cloud credentials not found. Firestore caching is disabled.")
    db = None
except Exception as e:
    print(f"  ! Firestore init error: {e}. Firestore caching is disabled.")
    db = None


async def save_recipe(recipe: dict) -> None:
    """
    Saves a recipe to Firestore recipes collection.
    Uses recipe ID as the document ID so we never duplicate.
    """
    if db is None:
        return

    recipe_id = str(recipe["id"])

    # Create a copy so we don't pollute the live session state with datetime objects
    # which break JSON serialization when sending to the frontend over WebSocket
    data = recipe.copy()
    data["cached_at"] = datetime.now(timezone.utc)

    await db.collection("recipes").document(recipe_id).set(data)
    print(f"  ✓ Saved recipe to Firestore: {recipe['name']} (id: {recipe_id})")


async def get_recipe_by_id(recipe_id: str) -> dict | None:
    """
    Fetch a single recipe by its ID.
    Returns None if not found.
    """
    if db is None:
        return None

    doc = await db.collection("recipes").document(recipe_id).get()

    if doc.exists:
        data = doc.to_dict()
        # Remove datetime objects before returning to avoid JSON serialization errors
        if "cached_at" in data:
            del data["cached_at"]
        return data
    return None


async def recipe_exists(recipe_id: str) -> bool:
    """
    Check if a recipe is already cached before saving.
    Avoids overwriting with less complete data.
    """
    if db is None:
        return False

    doc = await db.collection("recipes").document(recipe_id).get()
    return doc.exists


async def get_all_recipes() -> list:
    """
    Returns all cached recipes.
    Used for browsing before a user has searched anything.
    """
    if db is None:
        return []

    docs = db.collection("recipes").stream()
    recipes = []
    async for doc in docs:
        recipes.append(doc.to_dict())
    return recipes


async def search_recipes_by_name(query: str) -> list:
    """
    Basic name search in Firestore.
    Used for quick lookups of already-cached recipes only.
    """
    if db is None:
        return []

    docs = db.collection("recipes").stream()
    results = []
    query_lower = query.lower()

    async for doc in docs:
        data = doc.to_dict()
        if query_lower in data.get("name", "").lower():
            results.append(data)

    return results

async def get_cached_search(ingredients: list) -> list | None:
    """
    Check if we've already generated recipes for this exact ingredient list.
    Returns the recipes list if found, otherwise None.
    """
    if db is None:
        return None

    sorted_ingredients = sorted([i.lower().strip() for i in ingredients])
    query_hash = hashlib.md5(",".join(sorted_ingredients).encode()).hexdigest()
    
    doc = await db.collection("searches").document(query_hash).get()
    if doc.exists:
        data = doc.to_dict()
        print(f"  ✓ Cache hit for ingredients: {ingredients} -> hash: {query_hash}")
        recipes = data.get("recipes", [])
        # Clean datetime objects
        for r in recipes:
            if "cached_at" in r:
                del r["cached_at"]
        return recipes
    return None

async def save_cached_search(ingredients: list, recipes: list) -> None:
    """
    Save Gemini's generated recipes for an ingredient list to avoid hitting the API again.
    """
    if db is None:
        return

    sorted_ingredients = sorted([i.lower().strip() for i in ingredients])
    query_hash = hashlib.md5(",".join(sorted_ingredients).encode()).hexdigest()
    
    await db.collection("searches").document(query_hash).set({
        "ingredients": sorted_ingredients,
        "recipes": recipes, # recipes are already clean dictionaries
        "cached_at": datetime.now(timezone.utc)
    })
    print(f"  ✓ Cached new search results for hash: {query_hash}")
