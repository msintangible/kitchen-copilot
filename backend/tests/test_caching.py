import asyncio
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from backend.services.tool import handle_search_recipes, handle_search_recipe_by_name

async def test_cache():
    print("\n--- Test 1: Ingredient Search ---")
    ingredients = ["chicken", "rice", "broccoli"]
    
    print("Call 1 (Should hit Gemini API and cache it):")
    res1 = await handle_search_recipes(ingredients)
    
    print("\nCall 2 (Should hit Firestore Cache instantly):")
    res2 = await handle_search_recipes(ingredients)

    print("\nCall 3 (Different order, should still hit Cache):")
    res3 = await handle_search_recipes(["rice", "broccoli", "chicken"])

    print("\n--- Test 2: Recipe Name Search ---")
    recipe_name = "Chicken and Rice Bowl"
    
    print("Call 1 (Should hit Gemini/Spoonacular API and cache it):")
    res4 = await handle_search_recipe_by_name(recipe_name)
    
    print("\nCall 2 (Should hit Firestore Cache instantly):")
    res5 = await handle_search_recipe_by_name(recipe_name)
    
    print("\n--- Done ---")

if __name__ == "__main__":
    asyncio.run(test_cache())
