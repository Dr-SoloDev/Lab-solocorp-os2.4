"""Central Bus package.

``__version__`` is the SINGLE source of truth for the Central Bus service
version. Every other module imports it from here — never re-declare a version
literal in ``main.py`` or ``health.py`` (drift gate:
``tests/test_version_single_source.py``).

It must be assigned before the submodule imports below so that
``from central_bus import __version__`` works even during a partial package
initialisation (e.g. ``import central_bus.health``).
"""

__version__ = "0.6.2"

from .models import BusMessage
from . import open_design
from .config import settings
from .queue import enqueue, dequeue, drain, requeue, list_dead_letters, SQLiteQueueManager
from .router import route, priority_for, RoutingEngine
from .state import init_project, get as get_state, update_phase, run_pipeline_guards
from .audit import log as audit_log, read as audit_read
from .exceptions import classify, handle, escalate, read_escalations
from .dashboard import summary, all_projects, render, owner_dashboard
from .qa_gate import check, advance
from .webhook_receiver import receive_webhook, poll_all_watched
from .monitor_watchdog import watchdog_loop, process_queue

__all__ = [
    "__version__",
    "BusMessage", "settings",
    "enqueue", "dequeue", "drain", "requeue", "list_dead_letters", "SQLiteQueueManager",
    "route", "priority_for", "RoutingEngine",
    "init_project", "get_state", "update_phase", "run_pipeline_guards",
    "audit_log", "audit_read",
    "classify", "handle", "escalate", "read_escalations",
    "summary", "all_projects", "render",
    "check", "advance",
    "receive_webhook", "poll_all_watched",
    "watchdog_loop", "process_queue",
]
