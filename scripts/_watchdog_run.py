from central_bus.monitor_watchdog import watchdog_loop, check_dead_letters
import sys

processed = watchdog_loop(max_iterations=5)
stuck = check_dead_letters()

if processed > 0:
    print(f"[OK] Watchdog processed {processed} messages")
if stuck:
    print(f"[WARN] Dead letters: {len(stuck)} stuck messages")
if processed == 0 and not stuck:
    pass
