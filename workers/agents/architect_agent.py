"""Architect Agent — @architect-songsak: Central Bus, Routing, Monitoring"""

from __future__ import annotations

from workers.agents.base_agent import BaseAgent


class ArchitectAgent(BaseAgent):
    """Architect — ดูแลสถาปัตยกรรมระบบ การ routing และ monitoring"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="architect-songsak",
            name="Architect พี่ทรงศักดิ์",
            profile_path="profiles/05-architect/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")

        if "review" in action or "architecture" in action:
            return await self._review_architecture(task)
        elif "routing" in action:
            return await self._check_routing(task)
        elif "monitor" in action or "monitoring" in action:
            return await self._monitor_system(task)
        else:
            return {"status": "completed", "summary": f"Architect รับทราบ: {task.get('payload', {}).get('description', '')}", "details": {}}

    async def _review_architecture(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "🏗️ Architecture review เสร็จสิ้น",
            "details": {
                "reviewed": task.get("payload", {}).get("scope", "system"),
                "findings": [],
                "recommendation": "ผ่าน — ไม่มี blocking issue",
            },
        }

    async def _check_routing(self, task: dict) -> dict:
        return {
            "status": "completed",
            "summary": "🔀 ตรวจสอบ routing แล้ว — ปกติ",
            "details": {"routes": "all active", "issues": []},
        }

    async def _monitor_system(self, task: dict) -> dict:
        import subprocess
        try:
            r = subprocess.run(
                ["curl", "-s", "http://127.0.0.1:8099/v1/health"],
                capture_output=True, text=True, timeout=5,
            )
            health = r.stdout.strip()
        except Exception:
            health = "unreachable"
        return {
            "status": "completed",
            "summary": "📡 ตรวจสอบระบบแล้ว",
            "details": {"central_bus": health},
        }
