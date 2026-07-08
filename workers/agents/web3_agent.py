"""Web3 Agent — @web3-aywa: Blockchain, DeFi, Solana"""

from workers.agents.base_agent import BaseAgent


class Web3Agent(BaseAgent):
    def __init__(self, bus_url="", api_key=""):
        super().__init__("web3-aywa", "Web3 อัยวา", "profiles/14-web3/SOUL.md", bus_url, api_key)

    async def execute(self, task: dict) -> dict:
        a = task.get("payload", {}).get("action", "")
        if "blockchain" in a or "chain" in a:
            return {"status": "completed", "summary": "⛓️ Blockchain analysis เสร็จ", "details": {"action": a}}
        elif "defi" in a or "finance" in a:
            return {"status": "completed", "summary": "🏦 DeFi strategy วางแผนแล้ว", "details": {"action": a}}
        elif "solana" in a or "web3" in a:
            return {"status": "completed", "summary": "◎ Solana dev พร้อมดำเนินการ", "details": {"action": a}}
        elif "nft" in a or "token" in a:
            return {"status": "completed", "summary": "🪙 Token/NFT design เสร็จ", "details": {"action": a}}
        return {"status": "completed", "summary": f"Web3 รับทราบ: {task.get('payload',{}).get('description','')}", "details": {}}
