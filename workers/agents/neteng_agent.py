"""Network Engineering Agent — @neteng-neet: Network, CDN, VPN, DNS, Infrastructure

Capabilities:
- Network topology design
- CDN/DNS configuration
- VPN setup and troubleshooting
- Load balancer configuration
- Infrastructure monitoring
"""

from __future__ import annotations

import json

from workers.agents.base_agent import BaseAgent


class NetEngAgent(BaseAgent):
    """Network Engineer — ดูแล Network, CDN, VPN, DNS, Infrastructure"""

    NETWORK_DOMAINS = {
        "dns": ["dns", "domain", "nameserver", "zone"],
        "cdn": ["cdn", "cloudfront", "cloudflare", "akamai", "fastly"],
        "vpn": ["vpn", "tunnel", "wireguard", "openvpn", "ipsec"],
        "lb": ["load balancer", "nginx", "haproxy", "traffic"],
        "bgp": ["bgp", "ospf", "routing", "peering"],
        "monitor": ["monitor", "ping", "latency", "bandwidth", "snmp"],
    }

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="neteng-neet",
            name="NetEng นีต",
            profile_path="profiles/16-neteng/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    def _detect_domain(self, action: str, description: str) -> str:
        combined = (action + " " + description).lower()
        for domain, keywords in self.NETWORK_DOMAINS.items():
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
                "summary": "NetEng Agent: ไม่มี description ใน payload",
                "details": {"error": "missing_description"},
            }

        domain = self._detect_domain(action, description)

        prompt = (
            f"คุณคือ Network Engineer (นีต) ของ SoloCorp OS\n"
            f"ขอบเขต: {domain}\n"
            f"ได้รับงานจาก CEO: {description}\n"
        )
        if params:
            prompt += f"parameters: {json.dumps(params, ensure_ascii=False)}\n"
        prompt += "\nโปรดวิเคราะห์และเสนอแนวทางการดำเนินการ รายงานผล"

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
                "summary": f"NetEng รับทราบ: {description[:200]}",
                "details": {"action": action, "domain": domain, "llm_error": str(e)},
            }
