"""Web3 Agent — @web3-aywa: Blockchain, Smart Contracts, Solana, DeFi

Capabilities:
- Smart contract development (Solidity/Anchor)
- Blockchain security audit
- DeFi protocol analysis
- Tokenomics design
- Web3.js/Solana.js integration
"""

from __future__ import annotations

import json

from workers.agents.base_agent import BaseAgent


class Web3Agent(BaseAgent):
    """Web3 & DeFi — ดูแล Blockchain, Smart Contracts, Solana, DeFi"""

    DOMAINS = {
        "solidity": ["solidity", "evm", "ethereum", "contract", "erc"],
        "solana": ["solana", "anchor", "spl", "rust", "solana-program"],
        "defi": ["defi", "liquidity", "swap", "staking", "yield", "amm"],
        "security": ["audit", "vulnerability", "reentrancy", "overflow", "access control"],
        "nft": ["nft", "token", " mint", "collection", "metadata"],
    }

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="web3-aywa",
            name="Web3 อัยวา",
            profile_path="profiles/14-web3/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    def _detect_domain(self, action: str, description: str) -> str:
        combined = (action + " " + description).lower()
        for domain, keywords in self.DOMAINS.items():
            if any(kw in combined for kw in keywords):
                return domain
        return "general"

    async def execute(self, task: dict) -> dict:
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        params = payload.get("params", {})

        if not description:
            return {
                "status": "failed",
                "summary": "Web3 Agent: ไม่มี description ใน payload",
                "details": {"error": "missing_description"},
            }

        domain = self._detect_domain(action, description)

        prompt = (
            f"คุณคือ Web3 & DeFi (อัยวา) ของ SoloCorp OS\n"
            f"ขอบเขต: {domain}\n"
            f"ได้รับงานจาก CEO: {description}\n"
        )
        if params:
            prompt += f"parameters: {json.dumps(params, ensure_ascii=False)}\n"
        prompt += "\nโปรดวิเคราะห์และดำเนินการ รายงานผล"

        try:
            llm_response = await self.think(prompt, max_tokens=500)
            return {
                "status": "completed",
                "summary": llm_response[:300],
                "details": {
                    "action": action,
                    "domain": domain,
                    "agent": self.agent_id,
                    "llm_used": True,
                    "full_response": llm_response,
                },
            }
        except Exception as e:
            return {
                "status": "completed",
                "summary": f"Web3 รับทราบ: {description[:200]}",
                "details": {"action": action, "domain": domain, "llm_error": str(e)},
            }
