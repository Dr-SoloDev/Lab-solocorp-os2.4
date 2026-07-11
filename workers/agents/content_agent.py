"""Content Creator Agent — @content-creator-sek: Content, Creative, Media"""

from workers.agents.base_agent import BaseAgent


class ContentAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("content-creator-sek", "Content เสก", "profiles/15-content-creator/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"content": f"Content: {d}\nโปรดำสร้าง content และเสนอแนวทาง", "social": f"Social media: {d}\nโปรดำวางแผน content social", "video": f"Video/Creative: {d}\nโปรดำเสนอ concept", "caption": f"Caption: {d}\nโปรดำเขียน caption"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ Content Creator (เสก) ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ Content Creator (เสก) ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"Content รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
