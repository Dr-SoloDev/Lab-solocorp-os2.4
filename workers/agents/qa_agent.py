"""QA Agent — @qa: Testing, Quality, Evidence"""

from workers.agents.base_agent import BaseAgent


class QAAgent(BaseAgent):
    """QA — ดูแล testing, quality assurance, evidence"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__("qa", "QA ทีม", "profiles/10-qa/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"test": f"ทดสอบ: {d}\nโปรดวางแผน test cases และรายงานผล", "qa": f"Quality check: {d}\nโปรดตรวจสอบคุณภาพและรายงาน", "bug": f"Bug/Regression: {d}\nโปรดวิเคราะห์และรายงาน"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ QA ทีม ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ QA ทีม ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"QA รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
