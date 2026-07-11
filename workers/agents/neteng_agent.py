"""NetEng Agent — @neteng-neet: Network, Infra, CDN, VPN"""

from workers.agents.base_agent import BaseAgent


class NetEngAgent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("neteng-neet", "NetEng นีต", "profiles/16-neteng/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"network": f"Network/Infra: {d}\nโปรดำตรวจสอบและรายงาน", "cdn": f"CDN/DNS: {d}\nโปรดำตรวจสอบและ optimize", "vpn": f"VPN/Security: {d}\nโปรดำตรวจสอบ config", "monitor": f"Monitoring: {d}\nโปรดำรายงานสถานะ"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ NetEng (นีต) ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ NetEng (นีต) ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"NetEng รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
