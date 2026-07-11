"""Web3 Agent — @web3-aywa: Blockchain, DeFi, Solana"""

from workers.agents.base_agent import BaseAgent


class Web3Agent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("web3-aywa", "Web3 อัยวา", "profiles/14-web3/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        d = task.get("payload", {}).get("description", "")
        action_map = {"blockchain": f"Blockchain: {d}\nโปรดำวิเคราะห์และให้ข้อเสนอ", "defi": f"DeFi: {d}\nโปรดำเสนอ DeFi strategy", "solana": f"Solana: {d}\nโปรดำวางแผนพัฒนา", "nft": f"Token/NFT: {d}\nโปรดำเสนอ design"}
        prompt = None
        for k, v in action_map.items():
            if k in a:
                prompt = f"คุณคือ Web3 (อัยวา) ของ SoloCorp OS\n{v}"
                break
        if not prompt:
            prompt = f"คุณคือ Web3 (อัยวา) ของ SoloCorp OS\nได้รับงานจาก CEO: {d}\nโปรดำดำเนินการและรายงานผล"
        try:
            llm = await self.think(prompt, max_tokens=500)
            return {"status": "completed", "summary": llm[:200], "details": {"action": a, "llm_used": True, "full_response": llm}}
        except Exception as e:
            return {"status": "completed", "summary": f"Web3 รับทราบ: {d}", "details": {"action": a, "llm_error": str(e)}}
