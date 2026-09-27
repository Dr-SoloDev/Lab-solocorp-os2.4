from webhook_receiver import poll_all_watched
from monitor_watchdog import watchdog_loop, check_dead_letters
r = poll_all_watched()
p = sum(len(v) for v in r.values())
w = watchdog_loop(max_iterations=10)
s = check_dead_letters()
if p or w or s:
    parts = []
    if p: parts.append(f'{p} commits')
    if w: parts.append(f'{w} routed')
    if s: parts.append(f'{len(s)} stuck')
    print(' · '.join(parts))
