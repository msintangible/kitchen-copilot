import os
import httpx
from dotenv import load_dotenv
from google import genai
from google.genai import types


# Firestore is optional — app works without it (recipes won't be cached)
try:
    from backend.db.firestore_client import save_recipe, recipe_exists
except (ModuleNotFoundError, ImportError):
    try:
        from db.firestore_client import save_recipe, recipe_exists
    except (ModuleNotFoundError, ImportError):
        async def save_recipe(*a, **kw): pass
        async def recipe_exists(*a, **kw): return False
        print("  ⚠ Firestore not available — recipes won't be cached")

# Timer manager
try:
    from backend.services.timer import timer_manager
except (ModuleNotFoundError, ImportError):
    from services.timer import timer_manager

load_dotenv()


client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
SPOONACULAR_KEY = os.getenv("SPOONACULAR_API_KEY")
SPOONACULAR_BASE = "https://api.spoonacular.com"


# ── Session State (shared across tool calls within a session) ─────
# This stores the last fetched recipes so the frontend can be updated.
session_state = {
    "recipes": [],          # Last fetched recipe results
    "active_recipe": None,  # Currently selected recipe
    "pending_ui_commands": [],  # Queue of UI commands to send to frontend
}

def get_session_recipes():
    """Get the current recipe state for broadcasting to frontend."""
    return session_state["recipes"]

def get_active_recipe():
    """Get the currently selected recipe."""
    return session_state["active_recipe"]

def set_active_recipe(recipe_id: int):
    """Set the active recipe by its Spoonacular ID."""
    for r in session_state["recipes"]:
        if r["id"] == recipe_id:
            session_state["active_recipe"] = r
            return r
    return None

def pop_pending_ui_commands():
    """Pop all pending UI commands (drain the queue)."""
    commands = session_state["pending_ui_commands"][:]
    session_state["pending_ui_commands"] = []
    return commands

def reset_backend_state():
    """Reset the session state (recipes) and all active timers."""
    session_state["recipes"] = []
    session_state["active_recipe"] = None
    session_state["pending_ui_commands"] = []
    try:
        timer_manager.reset_all()
    except Exception as e:
        print(f"Error resetting timers: {e}")


# ── Gemini-powered recipe generation ─────────────────────────────────


async def fetch_recipe_by_name(recipe_name: str) -> dict:
    """
    Use Gemini to generate a clean, simple, classic version of a recipe by name.
    Much better than Spoonacular for name-based searches — Gemini gives standard
    home-cooking recipes, not overcomplicated restaurant versions.
    """
    import json
    import hashlib

    prompt = f"""You are a practical home-cooking assistant. Generate a simple, classic, straightforward recipe for "{recipe_name}".

RULES:
- This is a HOME COOKING recipe — keep it simple and accessible.
- Do NOT add exotic or unnecessary ingredients. Stick to the classic version.
- Steps should be clear, numbered, and each step is ONE action.
- Aim for 6-12 steps. Each step should be 1-2 sentences maximum.
- Ingredients should include realistic measurements (e.g. "2 cups", "1 tablespoon").

Return ONLY valid JSON in exactly this format, no markdown, no extra text:
{{
  "name": "Classic Spaghetti Bolognese",
  "ingredients": ["400g spaghetti", "500g ground beef", "1 onion, diced", "2 cloves garlic", "400g canned tomatoes", "2 tablespoons olive oil", "salt and pepper to taste"],
  "steps": [
    "Boil a large pot of salted water.",
    "Cook spaghetti according to package instructions until al dente.",
    "While pasta cooks, heat olive oil in a large pan over medium heat.",
    "Add onion and garlic, sauté for 3-4 minutes until softened.",
    "Add ground beef and cook, breaking it up, until browned.",
    "Pour in the canned tomatoes, season with salt and pepper.",
    "Simmer the sauce for 15 minutes until slightly thickened.",
    "Drain the pasta and serve topped with the Bolognese sauce."
  ]
}}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)

        # Generate a stable integer ID from the recipe name (so Firestore caching works)
        stable_id = int(hashlib.md5(recipe_name.lower().encode()).hexdigest()[:8], 16)

        return {
            "id": stable_id,
            "name": data.get("name", recipe_name.title()),
            "image": "",  # No image for AI-generated recipes
            "steps": data.get("steps", []),
            "missing_ingredients": data.get("ingredients", []),
            "match_percentage": 100,
        }

    except Exception as e:
        print(f"  ⚠ Gemini recipe generation failed: {e}")
        return {}



# ── Tool Definitions ───────────────────────────────────────────────

search_recipes_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_recipes",
            description=(
                "Search for recipes that match a list of ingredients the user has. "
                "Call this ONLY when the user mentions specific ingredients they have available "
                "and wants to know what they can cook with them. "
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

search_recipe_by_name_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="search_recipe_by_name",
            description=(
                "Look up a specific classic recipe by name. "
                "Use this when the user tells you EXACTLY what dish they want to cook, "
                "for example 'I want to make fried rice', 'let's cook chicken bolognese', "
                "or 'make me a classic carbonara'. "
                "This finds the most popular standard version of that recipe directly "
                "and goes straight to cooking — no ingredient matching needed."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "recipe_name": types.Schema(
                        type=types.Type.STRING,
                        description="The name of the dish the user wants to cook, e.g. 'fried rice', 'chicken bolognese'"
                    ),
                },
                required=["recipe_name"]
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

ui_command_tool = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="ui_command",
            description=(
                "Send a UI command to the frontend app. Use this when the user asks to "
                "show or hide the recipe sidebar, mute/unmute their microphone, or mark "
                "the current cooking step as done. Valid actions: "
                "'show_sidebar', 'hide_sidebar', 'toggle_mute', 'step_done', 'select_recipe', 'stop_session'."
            ),
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "action": types.Schema(
                        type=types.Type.STRING,
                        description="The UI action to perform: 'show_sidebar', 'hide_sidebar', 'toggle_mute', 'step_done', 'select_recipe', 'focus_timer', or 'stop_session'"
                    ),
                    "recipe_id": types.Schema(
                        type=types.Type.INTEGER,
                        description="The Spoonacular recipe ID, only needed when action is 'select_recipe'"
                    ),
                    "timer_id": types.Schema(
                        type=types.Type.STRING,
                        description="The ID of the timer to focus on, only needed when action is 'focus_timer'"
                    ),
                    "step_number": types.Schema(
                        type=types.Type.INTEGER,
                        description="The step number to mark as done (1-indexed), only needed when action is 'step_done'. If not provided, the current step is marked done and the next step becomes active."
                    ),
                },
                required=["action"]
            )
        )
    ]
)


# ── Tool Handlers ─────────────────────────────────────────────────

async def handle_search_recipes(ingredients: list) -> dict:
    """Use Gemini to suggest 3 practical recipes based on available ingredients."""
    print(f"\n  🔧 search_recipes called with: {ingredients}")
    import json, hashlib

    ingredients_list = ", ".join(ingredients)

    prompt = f"""You are a practical home-cooking assistant. The user has these ingredients: {ingredients_list}.

Suggest exactly 3 simple, home-cooking recipes they could make. Prioritise recipes that use MOST of the listed ingredients.

RULES:
- Keep recipes simple and classic (e.g. fried rice, omelette, pasta) — not gourmet versions.
- Steps should be clear, each step ONE action, 1-2 sentences max. Aim for 6-10 steps.
- All ingredient amounts must have measurements ("2 cups", "400g", "1 tablespoon").
- estimated_time: realistic total cook + prep time as a short string like "15 min" or "30 min".
- needs_count: how many EXTRA ingredients (not in the user's list) the recipe requires. Integer.

Return ONLY valid JSON — no markdown, no extra text:
{{
  "recipes": [
    {{
      "name": "Classic Omelette",
      "estimated_time": "10 min",
      "needs_count": 1,
      "ingredients": ["3 eggs", "1 tablespoon butter", "salt and pepper"],
      "steps": [
        "Crack the eggs into a bowl and whisk well.",
        "Heat butter in a non-stick pan over medium heat.",
        "Pour in the eggs and let them set slightly at the edges.",
        "Fold the omelette in half and slide onto a plate."
      ]
    }}
  ]
}}"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        data = json.loads(response.text)
        raw_recipes = data.get("recipes", [])

        recipes = []
        for r in raw_recipes[:3]:
            name = r.get("name", "Recipe")
            stable_id = int(hashlib.md5(name.lower().encode()).hexdigest()[:8], 16)
            image_url = f"https://source.unsplash.com/400x300/?{name.replace(' ', '+')},food,cooking"

            formatted = {
                "id": stable_id,
                "name": name,
                "estimated_time": r.get("estimated_time", ""),
                "needs_count": r.get("needs_count", 0),
                "match_percentage": 100,  # kept for backward compat
                "missing_ingredients": r.get("ingredients", []),
                "image": "",  # emoji handled in the frontend
                "steps": r.get("steps", [])
            }
            recipes.append(formatted)

            already_saved = await recipe_exists(str(stable_id))
            if not already_saved:
                await save_recipe(formatted)

        session_state["recipes"] = recipes
        session_state["pending_ui_commands"].append({
            "type": "recipe_results",
            "recipes": recipes
        })

        print(f"  ✓ Generated {len(recipes)} recipes via Gemini")
        return {"recipes": recipes}

    except Exception as e:
        print(f"  ✗ Gemini recipe generation error: {e}")
        return {"error": str(e), "recipes": []}


async def handle_search_recipe_by_name(recipe_name: str) -> dict:
    """Fetch a standard recipe by name and load it directly into the session."""
    print(f"\n  🔧 search_recipe_by_name called with: {recipe_name}")

    try:
        recipe = await fetch_recipe_by_name(recipe_name)
        if not recipe or not recipe.get("steps"):
            return {"error": f"Could not find a recipe for '{recipe_name}'. Try a different name."}

        # Store in session (both as recipe list and immediately as active)
        session_state["recipes"] = [recipe]
        session_state["active_recipe"] = recipe

        # Push directly to sidebar — no picker needed
        session_state["pending_ui_commands"].append({
            "type": "recipe_selected",
            "recipe": recipe
        })

        # Also cache to Firestore
        already_saved = await recipe_exists(str(recipe["id"]))
        if not already_saved:
            await save_recipe(recipe)

        print(f"  ✓ Loaded recipe by name: {recipe['name']} ({len(recipe['steps'])} steps)")
        step_count = len(recipe["steps"])
        return {
            "recipe_id": recipe["id"],
            "name": recipe["name"],
            "step_count": step_count,
            "message": f"Found '{recipe['name']}' with {step_count} steps. It's now showing on screen."
        }

    except Exception as e:
        print(f"  ✗ search_recipe_by_name error: {e}")
        return {"error": str(e)}


async def handle_set_cooking_timer(name: str, minutes: int) -> dict:
    """Create a new cooking timer"""
    print(f"\n  ⏰ set_cooking_timer called: '{name}' for {minutes} minutes")

    def timer_complete_callback(timer):
        print(f"\n  🔔 Timer finished internally: {timer.name}")
        # Insert a special UI command that will be intercepted by gemini_live.py
        # to trigger a system pronunciation.
        session_state["pending_ui_commands"].append({
            "type": "timer_complete",
            "timer_id": timer.id,
            "timer_name": timer.name
        })

    try:
        timer_id = timer_manager.create_timer(name, minutes, callback=timer_complete_callback)
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


async def handle_ui_command(action: str, recipe_id: int = None, timer_id: str = None, step_number: int = None) -> dict:
    """Handle UI commands from Gemini to control the frontend."""
    print(f"\n  🎛️ ui_command called: action={action}, recipe_id={recipe_id}, timer_id={timer_id}, step_number={step_number}")

    if action == "select_recipe" and recipe_id is not None:
        recipe = set_active_recipe(recipe_id)
        if recipe:
            session_state["pending_ui_commands"].append({
                "type": "recipe_selected",
                "recipe": recipe
            })
            return {"status": "ok", "message": f"Selected recipe: {recipe['name']}"}
        else:
            return {"error": f"Recipe {recipe_id} not found in recent results."}
    else:
        # For show/hide/mute/step_done/focus_timer — just queue the command
        cmd = {
            "type": "ui_command",
            "action": action
        }
        if timer_id:
            cmd["timer_id"] = timer_id
        if step_number is not None:
            cmd["step_number"] = step_number
            
        session_state["pending_ui_commands"].append(cmd)
        return {"status": "ok", "action": action}


# ── Tool Router ───────────────────────────────────────────────────

TOOL_HANDLERS = {
    "search_recipes": handle_search_recipes,
    "search_recipe_by_name": handle_search_recipe_by_name,
    "set_cooking_timer": handle_set_cooking_timer,
    "start_timer": handle_start_timer,
    "pause_timer": handle_pause_timer,
    "stop_timer": handle_stop_timer,
    "get_timer_status": handle_get_timer_status,
    "list_all_timers": handle_list_all_timers,
    "ui_command": handle_ui_command,
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
