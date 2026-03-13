#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the current directory to the path so we can import timer
sys.path.insert(0, os.path.dirname(__file__))

from services.timer import set_timer, start_timer, get_timers

async def test_timers():
    print(" Testing Kitchen Timer System...\n")

    # Create some timers
    timer1_id = set_timer("Boil pasta", 10)
    timer2_id = set_timer("Bake chicken", 25)
    timer3_id = set_timer("Chill dessert", 60)

    print(" Created timers:")
    for timer in get_timers():
        print(f"  - {timer['name']}: {timer['total_seconds'] // 60} minutes")

    print("\n Starting timers...")
    start_timer(timer1_id)
    await asyncio.sleep(2)  # Wait 2 seconds
    start_timer(timer2_id)

    print("\n Current status:")
    for timer in get_timers():
        status = timer['status']
        remaining = timer['remaining_seconds'] // 60
        print(f"  - {timer['name']}: {status} ({remaining} min remaining)")

    # Let timers run for a bit
    await asyncio.sleep(5)

    print("\n Final status:")
    for timer in get_timers():
        status = timer['status']
        remaining = timer['remaining_seconds'] // 60
        print(f"  - {timer['name']}: {status} ({remaining} min remaining)")

    print("\n Timer system test completed!")

if __name__ == "__main__":
    asyncio.run(test_timers())
