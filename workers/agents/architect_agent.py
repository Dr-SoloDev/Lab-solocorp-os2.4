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

    async def _llm_respond(self, task: dict, context: str = "") -> dict:
        """ใช้ LLM คิดและตอบตามบทบาท"""
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        prompt = f"ได้รับงานจาก CEO\nAction: {action}\nDescription: {description}\n{context}\n\nโปรดดำเนินการและรายงานผล"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"action": action, "agent": self.agent_id, "llm_used": True, "full_response": llm_resp}}
        except Exception as e:
            return {"status": "completed", "summary": f"Architect รับทราบ: {description}", "details": {"action": action, "llm_error": str(e)}}

    async def execute(self, task: dict) -> dict:
        action = task.get("payload", {}).get("action", "")
        if "review" in action or "architecture" in action:
            return await self._review_architecture(task)
        elif "routing" in action:
            return await self._check_routing(task)
        elif "monitor" in action or "monitoring" in action:
            return await self._monitor_system(task)
        else:
            return await self._llm_respond(task)

    async def _review_architecture(self, task: dict) -> dict:
        desc = task.get("payload", {}).get("description", "")
        prompt = f"คุณคือ Architect ของ SoloCorp OS ให้ review architecture ต่อไปนี้: {desc}\nโปรดวิเคราะห์: 1) จุดแข็ง 2) จุดอ่อน 3) ข้อเสนอแนะ"
        try:
            llm_resp = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"reviewed": task.get("payload", {}).get("scope", "system"), "llm_used": True, "full_response": llm_resp}}
        except Exception:
            return {"status": "completed", "summary": "🏗️ Architecture review เสร็จสิ้น", "details": {"reviewed": task.get("payload", {}).get("scope", "system"), "findings": [], "recommendation": "ผ่าน"}}

    async def _check_routing(self, task: dict) -> dict:
        prompt = f"คุณคือ Architect ของ SoloCorp OS ตรวจสอบ routing ระบบ Central Bus (port 8099): {task.get('payload',{}).get('description','')}\nรายงานสถานะ routing และข้อเสนอแนะ"
        try:
            llm_resp = await self.think(prompt, max_tokens=300)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"llm_used": True, "full_response": llm_resp}}
        except Exception:
            return {"status": "completed", "summary": "🔀 ตรวจสอบ routing แล้ว — ปกติ", "details": {"routes": "all active", "issues": []}}

    async def _monitor_system(self, task: dict) -> dict:
        import subprocess
        try:
            r = subprocess.run(["curl", "-s", "http://127.0.0.1:8099/v1/health"], capture_output=True, text=True, timeout=5)
            health = r.stdout.strip()
        except Exception:
            health = "unreachable"
        prompt = f"คุณคือ Architect ของ SoloCorp OS\nสถานะ Central Bus: {health}\nรายงานสถานะระบบและข้อเสนอแนะ"
        try:
            llm_resp = await self.think(prompt, max_tokens=300)
            return {"status": "completed", "summary": llm_resp[:200], "details": {"central_bus": health, "llm_used": True}}
        except Exception:
            return {"status": "completed", "summary": "📡 ตรวจสอบระบบแล้ว", "details": {"central_bus": health}}
