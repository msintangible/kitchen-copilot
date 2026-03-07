
import os
import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
SPOONACULAR_KEY = os.getenv("SPOONACULAR_API_KEY")
SPOONACULAR_BASE = "https://api.spoonacular.com"


# ── Real Spoonacular calls ────────────────────────────────────────

async def fetch_recipes_by_ingredients(ingredients: list) -> list:
    """
    Step 1: Search by ingredients — returns basic recipe matches.
    Endpoint: /recipes/findByIngredients
    """
    async with httpx.AsyncClient() as http:
        response = await http.get(
            f"{SPOONACULAR_BASE}/recipes/findByIngredients",
            params={
                "apiKey": SPOONACULAR_KEY,
                "ingredients": ",".join(ingredients),
                "number": 3,           # top 3 results
                "ranking": 1,          # maximise used ingredients
                "ignorePantry": True   # ignore salt, water etc
            }
        )
        response.raise_for_status()
        return response.json()


async def fetch_recipe_steps(recipe_id: int) -> list:
    """
    Step 2: Get full step-by-step instructions for a recipe.
    Endpoint: /recipes/{id}/analyzedInstructions
    Called separately because findByIngredients doesn't include steps.
    """
    async with httpx.AsyncClient() as http:
        response = await http.get(
            f"{SPOONACULAR_BASE}/recipes/{recipe_id}/analyzedInstructions",
            params={"apiKey": SPOONACULAR_KEY}
        )
        response.raise_for_status()
        return response.json()


# ── Tool Definition ───────────────────────────────────────────────

search_recipes_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_recipes",
            description=(
                "Search for recipes that match a list of ingredients. "
                "Call this when the user mentions ingredients they have "
                "or wants to know what they can cook. "
                "Returns top 3 recipes ranked by ingredient match."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "ingredients": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(type=types.Type.STRING),
                        description="List of ingredients the user has available"
                    ),
                },
                required=["ingredients"]
            )
        )
    ]
)


# ── Tool Handler ──────────────────────────────────────────────────

async def handle_search_recipes(ingredients: list) -> dict:
    print(f"\n  🔧 search_recipes called with: {ingredients}")

    try:
        # Step 1 — find matching recipes
        raw_results = await fetch_recipes_by_ingredients(ingredients)

        recipes = []
        for r in raw_results:
            # Spoonacular gives used/missed ingredient counts
            total = r["usedIngredientCount"] + r["missedIngredientCount"]
            match_pct = round((r["usedIngredientCount"] / total) * 100) if total > 0 else 0
            missing = [i["name"] for i in r.get("missedIngredients", [])]

            recipes.append({
                "id": r["id"],
                "name": r["title"],
                "match_percentage": match_pct,
                "missing_ingredients": missing,
                "image": r.get("image", "")
            })

        print(f"  ✓ Found {len(recipes)} recipes from Spoonacular")
        return {"recipes": recipes}

    except Exception as e:
        print(f"  ✗ Spoonacular error: {e}")
        return {"error": str(e), "recipes": []}


# ── Tool Router ───────────────────────────────────────────────────

TOOL_HANDLERS = {
    "search_recipes": handle_search_recipes,
}


async def handle_tool_call(tool_name: str, tool_args: dict) -> dict:
    handler = TOOL_HANDLERS.get(tool_name)

    if not handler:
        print(f"  ⚠ Unknown tool: {tool_name}")
        return {"error": f"Tool {tool_name} not found"}

    return await handler(**tool_args)
if __name__ == "__main__":
    import asyncio

    async def test():
        print("Testing Spoonacular connection...\n")
        result = await handle_tool_call(
            "search_recipes",
            {"ingredients": ["pasta", "garlic", "eggs", "parmesan"]}
        )
        print("\nRecipes found:")
        for r in result.get("recipes", []):
            print(f"  - {r['name']} ({r['match_percentage']}% match)")
            if r['missing_ingredients']:
                print(f"    Missing: {', '.join(r['missing_ingredients'])}")

    asyncio.run(test())