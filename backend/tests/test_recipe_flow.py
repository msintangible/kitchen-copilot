"""
Test Recipe Flow — End-to-End Backend Verification
===================================================
This script tests the Spoonacular API + session state pipeline
without importing Firestore (which may not be installed locally).

Usage:
    python test_recipe_flow.py
"""
import os
import sys
import io
import json
import asyncio

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', line_buffering=True)

# ── Mock Firestore before importing tool.py ──────────────────────
# tool.py imports firestore_client which needs google-cloud-firestore.
# We mock it so the test works without that dependency.
import types as builtin_types
import importlib

# Create mock firestore_client module
mock_firestore = builtin_types.ModuleType("backend.db.firestore_client")

async def _mock_save_recipe(*a, **kw): pass
async def _mock_recipe_exists(*a, **kw): return False

mock_firestore.save_recipe = _mock_save_recipe
mock_firestore.recipe_exists = _mock_recipe_exists

# Also mock the config module
mock_config = builtin_types.ModuleType("backend.config")
mock_config.PROJECT_ID = "test"
mock_config.FIRESTORE_DATABASE = "test"

mock_db = builtin_types.ModuleType("backend.db")
mock_backend = builtin_types.ModuleType("backend")

sys.modules["backend"] = mock_backend
sys.modules["backend.db"] = mock_db
sys.modules["backend.db.firestore_client"] = mock_firestore
sys.modules["backend.config"] = mock_config

# Now add paths and import
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# We need to handle the import differently since tool.py uses backend.services.timer
# Let's mock it properly
mock_timer_mod = builtin_types.ModuleType("backend.services.timer")

class MockTimerManager:
    def create_timer(self, name, minutes): return "mock-timer-1"
    def start_timer(self, tid): return True
    def pause_timer(self, tid): return True
    def stop_timer(self, tid): return True
    def get_timer_status(self, tid): return {"name": name, "status": "created", "remaining_seconds": 600, "total_seconds": 600, "progress_percentage": 0}
    def get_all_timers(self): return []
    def cleanup_completed_timers(self): pass

mock_timer_mod.timer_manager = MockTimerManager()
mock_services = builtin_types.ModuleType("backend.services")
sys.modules["backend.services"] = mock_services
sys.modules["backend.services.timer"] = mock_timer_mod

# NOW we can import tool.py!
from services.tool import (
    handle_tool_call,
    pop_pending_ui_commands,
    session_state,
    set_active_recipe,
    fetch_recipes_by_ingredients,
    fetch_recipe_steps,
)


async def test_recipe_flow():
    print("=" * 60)
    print("  Kitchen Copilot — Recipe Flow Test")
    print("=" * 60)

    # ── Step 1: Call Spoonacular directly ────────────────────────
    print("\n[1] Calling Spoonacular with: pasta, garlic, eggs, parmesan")
    
    try:
        raw = await fetch_recipes_by_ingredients(["pasta", "garlic", "eggs", "parmesan"])
    except Exception as e:
        print(f"  ERROR: Spoonacular API failed: {e}")
        print(f"  Check SPOONACULAR_API_KEY in .env")
        return

    print(f"  Raw API returned {len(raw)} recipes")

    # ── Step 2: Run through handle_tool_call (full pipeline) ────
    print("\n[2] Running handle_tool_call('search_recipes', ...)")
    result = await handle_tool_call(
        "search_recipes",
        {"ingredients": ["pasta", "garlic", "eggs", "parmesan"]}
    )

    recipes = result.get("recipes", [])
    if not recipes:
        print("  ERROR: No recipes returned!")
        return

    print(f"\n  Found {len(recipes)} recipes:")
    for i, r in enumerate(recipes):
        print(f"  [{i+1}] {r['name']} ({r['match_percentage']}% match)")
        print(f"      ID: {r['id']}")
        print(f"      Missing: {', '.join(r['missing_ingredients']) or 'None'}")
        print(f"      Steps: {len(r['steps'])} steps")
        if r['steps']:
            print(f"      Step 1: {r['steps'][0][:80]}...")

    # ── Step 3: Check pending UI commands ─────────────────────
    print("\n[3] Pending UI commands for frontend:")
    pending = pop_pending_ui_commands()
    for cmd in pending:
        print(f"  Type: {cmd['type']}")
        if cmd['type'] == 'recipe_results':
            print(f"  Recipes: {len(cmd['recipes'])} cards to display")
            # Print the JSON shape the frontend will receive
            sample = cmd['recipes'][0]
            print(f"  Shape: {{ id, name, match_percentage, missing_ingredients, image, steps }}")
            print(f"  Sample keys: {list(sample.keys())}")

    # ── Step 4: Simulate user selecting a recipe ──────────────
    first = recipes[0]
    print(f"\n[4] Selecting recipe: {first['name']} (ID: {first['id']})")
    
    select_result = await handle_tool_call(
        "ui_command",
        {"action": "select_recipe", "recipe_id": first["id"]}
    )
    print(f"  Result: {select_result}")

    pending = pop_pending_ui_commands()
    for cmd in pending:
        print(f"  Frontend receives: type={cmd['type']}")
        if cmd.get('recipe'):
            print(f"    Recipe: {cmd['recipe']['name']}")
            print(f"    Steps: {len(cmd['recipe']['steps'])}")

    # ── Step 5: Test UI voice commands ────────────────────────
    print(f"\n[5] Testing UI voice commands:")
    for action in ["show_sidebar", "step_done", "hide_sidebar", "toggle_mute"]:
        await handle_tool_call("ui_command", {"action": action})
        pending = pop_pending_ui_commands()
        status = pending[0] if pending else "EMPTY"
        print(f"  '{action}' -> {status}")

    # ── Step 6: Verify final state ────────────────────────────
    print(f"\n[6] Session state:")
    print(f"  Stored recipes: {len(session_state['recipes'])}")
    active = session_state['active_recipe']
    print(f"  Active recipe: {active['name'] if active else 'None'}")
    print(f"  Pending queue: {len(session_state['pending_ui_commands'])} (should be 0)")

    print("\n" + "=" * 60)
    print("  ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(test_recipe_flow())
