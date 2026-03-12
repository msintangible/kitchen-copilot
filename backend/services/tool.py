import os
import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types

from backend.db.firestore_client import save_recipe, recipe_exists
from backend.services.timer import timer_manager

load_dotenv()
from backend.services.timer import timer_manager


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

timer_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="set_cooking_timer",
            description=(
                "Set a timer for a cooking step. Use this when the user wants to set a timer "
                "for a specific cooking task like 'boil pasta for 10 minutes' or 'bake chicken for 25 minutes'. "
                "Returns the timer ID for later reference."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "name": types.Schema(
                        type=types.Type.STRING,
                        description="Descriptive name for the timer (e.g., 'Boil pasta', 'Bake chicken')"
                    ),
                    "minutes": types.Schema(
                        type=types.Type.INTEGER,
                        description="Duration in minutes for the timer"
                    ),
                },
                required=["name", "minutes"]
            )
        ),
        types.FunctionDeclaration(
            name="start_timer",
            description=(
                "Start a previously created timer. Use this when the user wants to begin timing a cooking step."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "timer_id": types.Schema(
                        type=types.Type.STRING,
                        description="The ID of the timer to start"
                    ),
                },
                required=["timer_id"]
            )
        ),
        types.FunctionDeclaration(
            name="pause_timer",
            description=(
                "Pause a running timer. Use this when the user needs to temporarily stop timing."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "timer_id": types.Schema(
                        type=types.Type.STRING,
                        description="The ID of the timer to pause"
                    ),
                },
                required=["timer_id"]
            )
        ),
        types.FunctionDeclaration(
            name="stop_timer",
            description=(
                "Stop and reset a timer completely. Use this when the user wants to cancel a timer."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "timer_id": types.Schema(
                        type=types.Type.STRING,
                        description="The ID of the timer to stop"
                    ),
                },
                required=["timer_id"]
            )
        ),
        types.FunctionDeclaration(
            name="get_timer_status",
            description=(
                "Check the status of a specific timer. Use this when the user asks about a timer's progress."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "timer_id": types.Schema(
                        type=types.Type.STRING,
                        description="The ID of the timer to check"
                    ),
                },
                required=["timer_id"]
            )
        ),
        types.FunctionDeclaration(
            name="list_all_timers",
            description=(
                "Get the status of all active timers. Use this when the user wants to see all their current timers."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
                required=[]
            )
        ),
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

            # STEP 1: fetch instructions
            instructions = await fetch_recipe_steps(r["id"])

            steps = []
            if instructions:
                for step in instructions[0].get("steps", []):
                    steps.append(step["step"])

            formatted = {
                "id": r["id"],
                "name": r["title"],
                "match_percentage": match_pct,
                "missing_ingredients": missing,
                "image": r.get("image", ""),
                "steps": steps  # ← ADD THIS
            }

            recipes.append(formatted)

            # Step 3 — save to Firestore if not already there
            already_saved = await recipe_exists(str(r["id"]))
            if not already_saved:
                await save_recipe(formatted)
                print("saved to firestore database")
            else:
                print(f"  → Already in Firestore: {r['title']}")

        print(f"  OK Found {len(recipes)} recipes from Spoonacular")
        return {"recipes": recipes}

    except Exception as e:
        print(f"  ✗ Spoonacular error: {e}")
        return {"error": str(e), "recipes": []}


async def handle_set_cooking_timer(name: str, minutes: int) -> dict:
    """Create a new cooking timer"""
    print(f"\n  ⏰ set_cooking_timer called: '{name}' for {minutes} minutes")

    try:
        timer_id = timer_manager.create_timer(name, minutes)
        print(f"  OK Created timer '{name}' ({minutes} min) with ID: {timer_id}")
        return {
            "timer_id": timer_id,
            "name": name,
            "minutes": minutes,
            "status": "created",
            "message": f"Timer '{name}' set for {minutes} minutes. Use start_timer to begin."
        }
    except Exception as e:
        print(f"  ✗ Timer creation error: {e}")
        return {"error": str(e)}


async def handle_start_timer(timer_id: str) -> dict:
    """Start a timer"""
    print(f"\n  ▶️ start_timer called for: {timer_id}")

    try:
        success = timer_manager.start_timer(timer_id)
        if success:
            timer_status = timer_manager.get_timer_status(timer_id)
            print(f"  OK Started timer: {timer_status['name']}")
            return {
                "timer_id": timer_id,
                "status": "started",
                "message": f"Timer '{timer_status['name']}' is now running for {timer_status['total_seconds'] // 60} minutes."
            }
        else:
            return {"error": f"Could not start timer {timer_id}. It may not exist or is already running."}
    except Exception as e:
        print(f"  ✗ Timer start error: {e}")
        return {"error": str(e)}


async def handle_pause_timer(timer_id: str) -> dict:
    """Pause a timer"""
    print(f"\n  ⏸️ pause_timer called for: {timer_id}")

    try:
        success = timer_manager.pause_timer(timer_id)
        if success:
            timer_status = timer_manager.get_timer_status(timer_id)
            remaining_min = timer_status['remaining_seconds'] // 60
            print(f"  OK Paused timer: {timer_status['name']} ({remaining_min} min remaining)")
            return {
                "timer_id": timer_id,
                "status": "paused",
                "remaining_minutes": remaining_min,
                "message": f"Timer '{timer_status['name']}' paused with {remaining_min} minutes remaining."
            }
        else:
            return {"error": f"Could not pause timer {timer_id}. It may not exist or is not running."}
    except Exception as e:
        print(f"  ✗ Timer pause error: {e}")
        return {"error": str(e)}


async def handle_stop_timer(timer_id: str) -> dict:
    """Stop a timer"""
    print(f"\n  ⏹️ stop_timer called for: {timer_id}")

    try:
        success = timer_manager.stop_timer(timer_id)
        if success:
            print(f"  OK Stopped timer: {timer_id}")
            return {
                "timer_id": timer_id,
                "status": "stopped",
                "message": f"Timer {timer_id} has been stopped and reset."
            }
        else:
            return {"error": f"Could not stop timer {timer_id}. It may not exist."}
    except Exception as e:
        print(f"  ✗ Timer stop error: {e}")
        return {"error": str(e)}


async def handle_get_timer_status(timer_id: str) -> dict:
    """Get status of a specific timer"""
    print(f"\n  📊 get_timer_status called for: {timer_id}")

    try:
        timer_status = timer_manager.get_timer_status(timer_id)
        if timer_status:
            remaining_min = timer_status['remaining_seconds'] // 60
            progress_pct = round(timer_status['progress_percentage'], 1)

            status_msg = f"Timer '{timer_status['name']}' is {timer_status['status']}"
            if timer_status['status'] == 'running':
                status_msg += f" with {remaining_min} minutes remaining ({progress_pct}% complete)"
            elif timer_status['status'] == 'paused':
                status_msg += f" (paused with {remaining_min} minutes remaining)"
            elif timer_status['status'] == 'completed':
                status_msg += " (finished!)"

            print(f"  OK {status_msg}")
            return {
                "timer_id": timer_id,
                **timer_status,
                "message": status_msg
            }
        else:
            return {"error": f"Timer {timer_id} not found."}
    except Exception as e:
        print(f"  ✗ Timer status error: {e}")
        return {"error": str(e)}


async def handle_list_all_timers() -> dict:
    """Get status of all timers"""
    print(f"\n  📋 list_all_timers called")

    try:
        timers = timer_manager.get_all_timers()
        print(f"  OK Found {len(timers)} timers")

        # Clean up old completed timers
        timer_manager.cleanup_completed_timers()

        return {
            "timers": timers,
            "count": len(timers),
            "message": f"You have {len(timers)} active timers."
        }
    except Exception as e:
        print(f"  ✗ List timers error: {e}")
        return {"error": str(e), "timers": []}


# ── Tool Router ───────────────────────────────────────────────────

TOOL_HANDLERS = {
    "search_recipes": handle_search_recipes,
    "set_cooking_timer": handle_set_cooking_timer,
    "start_timer": handle_start_timer,
    "pause_timer": handle_pause_timer,
    "stop_timer": handle_stop_timer,
    "get_timer_status": handle_get_timer_status,
    "list_all_timers": handle_list_all_timers,
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
        print("Testing Kitchen Copilot Tools...\n")

        # === Test recipe search ===
        print("=== Testing Recipe Search ===")
        result = await handle_tool_call(
            "search_recipes",
            {"ingredients": ["pasta", "garlic", "eggs", "parmesan"]}
        )

        recipes = result.get("recipes", [])

        print("\nRecipes found:")
        for r in recipes:
            print(f"  - {r['name']} ({r['match_percentage']}% match)")
            if r['missing_ingredients']:
                print(f"    Missing: {', '.join(r['missing_ingredients'])}")

        # === Verify Firestore Save ===
        print("\n=== Verifying Firestore Save ===")

        for r in recipes:
            exists = await recipe_exists(str(r["id"]))

            if exists:
                print(f"  ✓ Recipe saved in Firestore: {r['name']}")
            else:
                print(f"  ✗ Recipe NOT found in Firestore: {r['name']}")

        # === Timer Tests ===
        print("\n=== Testing Timer Functionality ===")

        timer_result = await handle_tool_call(
            "set_cooking_timer",
            {"name": "Boil pasta", "minutes": 10}
        )

        timer_id = timer_result.get("timer_id")
        print(f"Created timer: {timer_result.get('message')}")

        if timer_id:
            start_result = await handle_tool_call("start_timer", {"timer_id": timer_id})
            print(f"Started timer: {start_result.get('message')}")

            await asyncio.sleep(3)

            status_result = await handle_tool_call("get_timer_status", {"timer_id": timer_id})
            print(f"Timer status: {status_result.get('message')}")

            pause_result = await handle_tool_call("pause_timer", {"timer_id": timer_id})
            print(f"Paused timer: {pause_result.get('message')}")

        # === List timers ===
        list_result = await handle_tool_call("list_all_timers", {})

        print(f"\nAll timers: {list_result.get('message')}")

        for timer in list_result.get("timers", []):
            print(
                f"  - {timer['name']}: {timer['status']} "
                f"({timer['remaining_seconds']//60} min left)"
            )

    asyncio.run(test())
