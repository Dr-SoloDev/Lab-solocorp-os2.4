"""Content Creator Agent — @content-creator-sek: Content, Creative, Media"""

from workers.agents.base_agent import BaseAgent


class ContentAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("content-creator-sek", "Content เสก", "profiles/15-content-creator/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        if "content" in a or "write" in a or "copy" in a:
            return {"status": "completed", "summary": "✍️ Content created เรียบร้อย", "details": {"action": a}}
        elif "social" in a or "media" in a:
            return {"status": "completed", "summary": "📱 Social media content พร้อม", "details": {"action": a}}
        elif "video" in a or "creative" in a:
            return {"status": "completed", "summary": "🎬 Creative content เสร็จ", "details": {"action": a}}
        elif "caption" in a:
            return {"status": "completed", "summary": "💬 Caption เขียนเสร็จ", "details": {"action": a}}
        return {"status": "completed", "summary": f"Content รับทราบ: {task.get('payload',{}).get('description','')}", "details": {}}
