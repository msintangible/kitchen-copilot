import asyncio
import time
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass
from enum import Enum


class TimerStatus(Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"


@dataclass
class Timer:
    """Represents a single cooking timer"""
    id: str
    name: str
    duration_seconds: int
    remaining_seconds: int
    status: TimerStatus
    start_time: Optional[float] = None
    pause_time: Optional[float] = None
    callback: Optional[Callable] = None


class TimerManager:
    """Manages multiple concurrent cooking timers"""

    def __init__(self):
        self.timers: Dict[str, Timer] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}

    def create_timer(self, name: str, duration_minutes: int, callback: Optional[Callable] = None) -> str:
        """Create a new timer and return its ID"""
        timer_id = f"timer_{int(time.time())}_{len(self.timers)}"
        duration_seconds = duration_minutes * 60

        timer = Timer(
            id=timer_id,
            name=name,
            duration_seconds=duration_seconds,
            remaining_seconds=duration_seconds,
            status=TimerStatus.STOPPED,
            callback=callback
        )

        self.timers[timer_id] = timer
        return timer_id

    def start_timer(self, timer_id: str) -> bool:
        """Start a timer"""
        if timer_id not in self.timers:
            return False

        timer = self.timers[timer_id]
        if timer.status == TimerStatus.RUNNING:
            return True  # Already running

        if timer.status == TimerStatus.PAUSED:
            # Resume from paused state
            if timer.pause_time and timer.start_time:
                paused_duration = time.time() - timer.pause_time
                timer.start_time += paused_duration
        else:
            # Start fresh
            timer.start_time = time.time()
            timer.remaining_seconds = timer.duration_seconds

        timer.status = TimerStatus.RUNNING
        timer.pause_time = None

        # Start the async countdown task
        if timer_id in self._running_tasks:
            self._running_tasks[timer_id].cancel()

        self._running_tasks[timer_id] = asyncio.create_task(self._run_timer(timer_id))
        return True

    def pause_timer(self, timer_id: str) -> bool:
        """Pause a running timer"""
        if timer_id not in self.timers:
            return False

        timer = self.timers[timer_id]
        if timer.status != TimerStatus.RUNNING:
            return False

        timer.status = TimerStatus.PAUSED
        timer.pause_time = time.time()
        return True

    def stop_timer(self, timer_id: str) -> bool:
        """Stop a timer completely"""
        if timer_id not in self.timers:
            return False

        timer = self.timers[timer_id]
        timer.status = TimerStatus.STOPPED
        timer.remaining_seconds = timer.duration_seconds
        timer.start_time = None
        timer.pause_time = None

        if timer_id in self._running_tasks:
            self._running_tasks[timer_id].cancel()
            del self._running_tasks[timer_id]

        return True

    def get_timer_status(self, timer_id: str) -> Optional[Dict]:
        """Get the current status of a timer"""
        if timer_id not in self.timers:
            return None

        timer = self.timers[timer_id]
        current_time = time.time()

        if timer.status == TimerStatus.RUNNING and timer.start_time:
            elapsed = current_time - timer.start_time
            timer.remaining_seconds = max(0, timer.duration_seconds - int(elapsed))

        return {
            "id": timer.id,
            "name": timer.name,
            "status": timer.status.value,
            "remaining_seconds": timer.remaining_seconds,
            "total_seconds": timer.duration_seconds,
            "progress_percentage": ((timer.duration_seconds - timer.remaining_seconds) / timer.duration_seconds * 100) if timer.duration_seconds > 0 else 0
        }

    def get_all_timers(self) -> List[Dict]:
        """Get status of all timers"""
        return [self.get_timer_status(timer_id) for timer_id in self.timers.keys() if self.get_timer_status(timer_id)]

    def delete_timer(self, timer_id: str) -> bool:
        """Delete a timer"""
        if timer_id not in self.timers:
            return False

        if timer_id in self._running_tasks:
            self._running_tasks[timer_id].cancel()
            del self._running_tasks[timer_id]

        del self.timers[timer_id]
        return True

    async def _run_timer(self, timer_id: str):
        """Internal method to run the timer countdown"""
        try:
            timer = self.timers[timer_id]

            while timer.status == TimerStatus.RUNNING and timer.remaining_seconds > 0:
                await asyncio.sleep(1)
                timer.remaining_seconds -= 1

            if timer.status == TimerStatus.RUNNING:
                timer.status = TimerStatus.COMPLETED
                if timer.callback:
                    timer.callback(timer)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"Timer {timer_id} error: {e}")

    def cleanup_completed_timers(self):
        """Remove completed timers that have been finished for a while"""
        current_time = time.time()
        to_remove = []

        for timer_id, timer in self.timers.items():
            if timer.status == TimerStatus.COMPLETED:
                # Keep completed timers for 5 minutes, then remove
                if hasattr(timer, '_completed_time'):
                    if current_time - timer._completed_time > 300:  # 5 minutes
                        to_remove.append(timer_id)
                else:
                    timer._completed_time = current_time

        for timer_id in to_remove:
            del self.timers[timer_id]


# Global timer manager instance
timer_manager = TimerManager()


# Convenience functions for easy use
def set_timer(name: str, minutes: int, callback: Optional[Callable] = None) -> str:
    """Quick function to set a timer"""
    return timer_manager.create_timer(name, minutes, callback)


def start_timer(timer_id: str) -> bool:
    """Quick function to start a timer"""
    return timer_manager.start_timer(timer_id)


def pause_timer(timer_id: str) -> bool:
    """Quick function to pause a timer"""
    return timer_manager.pause_timer(timer_id)


def stop_timer(timer_id: str) -> bool:
    """Quick function to stop a timer"""
    return timer_manager.stop_timer(timer_id)


def get_timers() -> List[Dict]:
    """Quick function to get all timers"""
    return timer_manager.get_all_timers()


def get_timer(timer_id: str) -> Optional[Dict]:
    """Quick function to get a specific timer"""
    return timer_manager.get_timer_status(timer_id)


# Example usage and testing
async def timer_notification(timer: Timer):
    """Example callback for when timer completes"""
    print(f"🔔 Timer '{timer.name}' has finished! ({timer.duration_seconds // 60} minutes)")


if __name__ == "__main__":
    async def test_timers():
        print("Testing Kitchen Timer System...\n")

        # Create some timers
        timer1_id = set_timer("Boil pasta", 10, timer_notification)
        timer2_id = set_timer("Bake chicken", 25, timer_notification)
        timer3_id = set_timer("Chill dessert", 60, timer_notification)

        print("Created timers:")
        for timer in get_timers():
            print(f"  - {timer['name']}: {timer['total_seconds'] // 60} minutes")

        print("\nStarting timers...")
        start_timer(timer1_id)
        await asyncio.sleep(2)  # Wait 2 seconds
        start_timer(timer2_id)

        print("\nCurrent status:")
        for timer in get_timers():
            status = timer['status']
            remaining = timer['remaining_seconds'] // 60
            print(f"  - {timer['name']}: {status} ({remaining} min remaining)")

        # Let timers run for a bit
        await asyncio.sleep(5)

        print("\nFinal status:")
        for timer in get_timers():
            status = timer['status']
            remaining = timer['remaining_seconds'] // 60
            print(f"  - {timer['name']}: {status} ({remaining} min remaining)")

    asyncio.run(test_timers())
