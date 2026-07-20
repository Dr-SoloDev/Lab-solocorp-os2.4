#!/usr/bin/env python3
"""
🤖 Auto-Orchestrator — SoloCorp OS (Phase 8.4)
Watches bus/dispatch/ for new dispatches and auto-orchestrates:
  - Decompose task into sub-tasks
  - Assign to specialists
  - Track status (pending → in_progress → completed)
  - Report progress via bus/state/

Runs as a loop_runner loop (every 5 minutes) or can be called ad-hoc.
"""

import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

log = logging.getLogger(__name__)

BASE = Path(__file__).parent.parent.parent
DISPATCH_DIR = BASE / "bus/dispatch"
STATE_DIR = BASE / "bus/state"
QUEUE_DIR = BASE / "bus/queue"
TRACKER_FILE = STATE_DIR / ".orchestrator_tracker.json"

# ── Sub-task decomposition templates ──────────────────────────────────
DECOMPOSE_TEMPLATES = {
    "engineering": {
        "default": ["Analyze requirements", "Design solution", "Implement", "Test", "Review", "Deploy"],
        "api": ["Design API spec", "Implement endpoints", "Write tests", "Document", "Review"],
        "bug": ["Reproduce bug", "Root cause analysis", "Fix", "Test fix", "Verify"],
        "refactor": ["Audit existing code", "Plan changes", "Implement refactor", "Test regression", "Review"],
    },
    "design": {
        "default": ["Research & references", "Wireframe", "High-fidelity design", "Design review", "Handoff to dev"],
        "ux": ["User research", "Flow mapping", "Wireframe", "Prototype", "Usability test"],
        "visual": ["Mood board", "Visual concept", "Design system update", "Final design", "Asset export"],
    },
    "product": {
        "default": ["Problem validation", "PRD writing", "Stakeholder review", "Feature spec", "Handoff to dev"],
    },
    "qa": {
        "default": ["Test plan", "Test case writing", "Test execution", "Bug report", "Regression test"],
    },
}


class AutoOrchestrator:
    """Watches dispatches and auto-orchestrates pipeline"""
    
    def __init__(self):
        self.tracker = self._load_tracker()
    
    def _load_tracker(self) -> dict:
        if TRACKER_FILE.exists():
            try:
                return json.loads(TRACKER_FILE.read_text())
            except (json.JSONDecodeError, Exception):
                pass
        return {"dispatches": {}, "last_scan": ""}
    
    def _save_tracker(self):
        self.tracker["last_scan"] = datetime.now(timezone.utc).isoformat()
        TRACKER_FILE.parent.mkdir(parents=True, exist_ok=True)
        TRACKER_FILE.write_text(json.dumps(self.tracker, indent=2, ensure_ascii=False))
    
    def _get_department_from_dispatch(self, dispatch_data: dict) -> str:
        """Extract department from dispatch data"""
        cmd = dispatch_data.get("command", {})
        to_field = cmd.get("to", "")
        # Parse department from "to" field
        if isinstance(to_field, str):
            dept = to_field.split("(")[0].strip().lower()
            dept = dept.replace("@", "").replace("-head", "")
            # Map common names
            alias_map = {
                "architect-songsak": "architect", "พี่ทรงศักดิ์": "architect",
                "changful": "engineering", "ช่างฟูล": "engineering",
                "design-kreet": "design", "ครีเอท": "design",
                "product-produck": "product", "โปรดัค": "product",
                "cfo-meetoo": "cfo", "cmo-mark": "cmo",
                "orchestrator-wut": "orchestrator", "พี่วุฒิ": "orchestrator",
                "legal-tulya": "legal", "web3-aywa": "web3",
                "content-creator-sek": "content_creator",
            }
            for key, val in alias_map.items():
                if key in dept:
                    return val
        return cmd.get("department", "unknown")
    
    def _decompose_task(self, dispatch_data: dict) -> list[dict]:
        """Decompose a dispatch into sub-tasks"""
        cmd = dispatch_data.get("command", {})
        dept = self._get_department_from_dispatch(dispatch_data)
        title = cmd.get("title", "").lower()
        
        # Pick template
        templates = DECOMPOSE_TEMPLATES.get(dept, {"default": ["Review", "Execute", "Verify"]})
        
        # Match task type
        template_key = "default"
        for keyword, key in [("api", "api"), ("implement", "api"), ("endpoint", "api"),
                              ("bug", "bug"), ("fix", "bug"),
                              ("refactor", "refactor"), ("redesign", "refactor"),
                              ("ux", "ux"), ("research", "ux"), ("user", "ux"),
                              ("visual", "visual"), ("brand", "visual")]:
            if keyword in title:
                template_key = key
                break
        
        steps = templates.get(template_key, templates["default"])
        
        # Build sub-tasks
        tasks = []
        existing = cmd.get("tasks", [])
        for i, step in enumerate(steps):
            # If dispatch already has tasks, map them
            existing_desc = ""
            if i < len(existing):
                existing_desc = existing[i].get("description", "") if isinstance(existing[i], dict) else existing[i]
            
            tasks.append({
                "id": f"{dispatch_data.get('command', {}).get('id', 'TASK')}-{chr(65+i)}",
                "step": step,
                "description": existing_desc or f"{step} for: {cmd.get('title', 'task')}",
                "status": "pending",
                "assigned_to": dept,
            })
        
        # Add any extra existing tasks
        for i in range(len(steps), len(existing)):
            desc = existing[i].get("description", "") if isinstance(existing[i], dict) else existing[i]
            tasks.append({
                "id": f"{dispatch_data.get('command', {}).get('id', 'TASK')}-{chr(65+i)}",
                "step": f"Task {chr(65+i)}",
                "description": desc,
                "status": "pending",
                "assigned_to": dept,
            })
        
        return tasks
    
    def scan_new_dispatches(self) -> list[dict]:
        """Scan for new dispatches and orchestrate them"""
        results = []
        
        if not DISPATCH_DIR.exists():
            return results
        
        for date_dir in sorted(DISPATCH_DIR.iterdir(), reverse=True)[:7]:  # Last 7 days
            if not date_dir.is_dir():
                continue
            for f in sorted(date_dir.iterdir()):
                if f.suffix != ".json":
                    continue
                dispatch_id = f.stem
                
                # Skip already orchestrated
                if dispatch_id in self.tracker["dispatches"]:
                    continue
                
                try:
                    data = json.loads(f.read_text())
                    result = self._orchestrate(dispatch_id, data, date_dir.name)
                    results.append(result)
                except (json.JSONDecodeError, Exception) as exc:
                    log.warning("Failed to orchestrate %s: %s", dispatch_id, exc)
        
        self._save_tracker()
        return results
    
    def _orchestrate(self, dispatch_id: str, data: dict, date_str: str) -> dict:
        """Orchestrate a single dispatch"""
        cmd = data.get("command", {})
        dept = self._get_department_from_dispatch(data)
        priority = cmd.get("priority", "P2")
        
        # Skip already completed
        if data.get("status") in ("completed", "done", "cancelled"):
            self.tracker["dispatches"][dispatch_id] = {
                "status": "skipped",
                "reason": f"already {data['status']}",
            }
            return {"dispatch_id": dispatch_id, "status": "skipped"}
        
        # Decompose into sub-tasks
        sub_tasks = self._decompose_task(data)
        
        # Determine auto-level based on priority
        auto_level = {
            "P0": "manual",     # P0: CEO must handle
            "P1": "propose",    # P1: Auto-propose to dept head
            "P2": "auto",       # P2: Auto-assign to specialist
            "P3": "auto",       # P3: Auto-assign
        }.get(priority, "auto")
        
        # Create state entry
        state_entry = {
            "dispatch_id": dispatch_id,
            "date": date_str,
            "department": dept,
            "priority": priority,
            "title": cmd.get("title", ""),
            "auto_level": auto_level,
            "sub_tasks": sub_tasks,
            "status": "orchestrated" if auto_level == "auto" else "proposed",
            "orchestrated_at": datetime.now(timezone.utc).isoformat(),
            "total_tasks": len(sub_tasks),
            "completed_tasks": 0,
            "progress_pct": 0,
        }
        
        # Save state
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        state_file = STATE_DIR / f"{dispatch_id}.json"
        state_file.write_text(json.dumps(state_entry, indent=2, ensure_ascii=False))
        
        # Add to queue if auto-level (L1/L2)
        if auto_level == "auto":
            queue_file = QUEUE_DIR / "high.jsonl" if priority == "P0" else QUEUE_DIR / "normal.jsonl"
            queue_entry = {
                "dispatch_id": dispatch_id,
                "to": dept,
                "priority": priority,
                "timestamp": state_entry["orchestrated_at"],
                "status": "pending",
                "tasks": sub_tasks,
            }
            with open(queue_file, "a") as qf:
                qf.write(json.dumps(queue_entry) + "\n")
        
        # Update tracker
        self.tracker["dispatches"][dispatch_id] = {
            "status": state_entry["status"],
            "department": dept,
            "auto_level": auto_level,
            "total_tasks": len(sub_tasks),
            "orchestrated_at": state_entry["orchestrated_at"],
        }
        
        return {
            "dispatch_id": dispatch_id,
            "department": dept,
            "priority": priority,
            "auto_level": auto_level,
            "sub_tasks": len(sub_tasks),
            "status": state_entry["status"],
        }
    
    def get_status(self, dispatch_id: str) -> Optional[dict]:
        """Get orchestration status for a dispatch"""
        state_file = STATE_DIR / f"{dispatch_id}.json"
        if state_file.exists():
            try:
                return json.loads(state_file.read_text())
            except json.JSONDecodeError:
                pass
        return self.tracker["dispatches"].get(dispatch_id)
    
    def all_status(self) -> dict:
        """Get status of all tracked dispatches"""
        active = {}
        for did, info in self.tracker["dispatches"].items():
            if info.get("status") in ("orchestrated", "proposed", "in_progress"):
                active[did] = info
        
        return {
            "total_tracked": len(self.tracker["dispatches"]),
            "active": len(active),
            "last_scan": self.tracker.get("last_scan", ""),
            "dispatches": active,
        }
    
    def update_task_status(self, dispatch_id: str, task_id: str, new_status: str) -> Optional[dict]:
        """Update status of a specific sub-task"""
        state_file = STATE_DIR / f"{dispatch_id}.json"
        if not state_file.exists():
            return None
        
        try:
            state = json.loads(state_file.read_text())
        except json.JSONDecodeError:
            return None
        
        for task in state.get("sub_tasks", []):
            if task["id"] == task_id:
                task["status"] = new_status
                break
        
        # Recalculate progress
        total = len(state.get("sub_tasks", []))
        done = sum(1 for t in state.get("sub_tasks", []) if t["status"] in ("completed", "done"))
        state["completed_tasks"] = done
        state["progress_pct"] = int((done / total) * 100) if total > 0 else 0
        state["status"] = "completed" if done == total else "in_progress" if done > 0 else state["status"]
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        state_file.write_text(json.dumps(state, indent=2, ensure_ascii=False))
        
        # Update tracker
        if dispatch_id in self.tracker["dispatches"]:
            self.tracker["dispatches"][dispatch_id]["status"] = state["status"]
            self._save_tracker()
        
        return state


# ── CLI Usage ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    
    orch = AutoOrchestrator()
    
    if "--watch" in sys.argv:
        print("🤖 Auto-Orchestrator — watching bus/dispatch/...")
        print("  Press Ctrl+C to stop")
        import time
        try:
            while True:
                results = orch.scan_new_dispatches()
                for r in results:
                    icon = {"orchestrated": "✅", "proposed": "📋", "skipped": "⏭️"}.get(r["status"], "❓")
                    print(f"  {icon} {r['dispatch_id']} → {r['department']} [{r['auto_level']}] ({r['sub_tasks']} sub-tasks)")
                time.sleep(300)  # 5 min
        except KeyboardInterrupt:
            print("\n👋 Auto-Orchestrator stopped")
    
    elif "--status" in sys.argv:
        status = orch.all_status()
        print(f"Total tracked: {status['total_tracked']}, Active: {status['active']}")
        for did, info in list(status["dispatches"].items())[:10]:
            print(f"  {did}: {info['status']} ({info.get('department', '?')})")
    
    else:
        # One-shot scan
        results = orch.scan_new_dispatches()
        if results:
            for r in results:
                icon = {"orchestrated": "✅", "proposed": "📋", "skipped": "⏭️"}.get(r["status"], "❓")
                print(f"  {icon} {r['dispatch_id']} → {r['department']} [{r['auto_level']}] ({r['sub_tasks']} sub-tasks)")
        else:
            print("No new dispatches to orchestrate")
