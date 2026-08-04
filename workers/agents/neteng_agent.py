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

    # Rule-based SOP ต่อ domain — fallback เมื่อ LLM ไม่พร้อม
    DOMAIN_SOPS = {
        "dns": "ตรวจ TTL, nameserver propagation, DNSSEC, fallback resolver",
        "cdn": "ตรวจ cache hit ratio, edge POP, purge policy, origin health",
        "vpn": "ตรวจ tunnel status, key rotation, MTU, split-tunnel policy",
        "lb": "ตรวจ health check, session stickiness, TLS termination, backend pool",
        "bgp": "ตรวจ peering, prefix advertisement, route flap, AS-path",
        "monitor": "ตรวจ latency, packet loss, bandwidth utilization, uptime SLA",
        "general": "ตรวจ topology, dependency, runbook, escalation path",
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

        @staticmethod
        def _llm_usable(result: str) -> bool:
            return bool(result and not result.startswith("⚠️ LLM ไม่พร้อม"))

        def _sop_fallback(domain: str, description: str, action: str) -> dict:
            """Rule-based fallback — SOP ตาม domain แม้ LLM ล้ม"""
            sop = self.DOMAIN_SOPS.get(domain, self.DOMAIN_SOPS["general"])
            return {
                "status": "completed",
                "summary": f"[{domain.upper()}] SOP: {sop} — จาก: {description[:150]}",
                "details": {
                    "action": action,
                    "domain": domain,
                    "agent": self.agent_id,
                    "llm_used": False,
                    "fallback": "domain_sop",
                    "sop": sop,
                },
            }

        try:
            llm_response = await self.think(prompt, max_tokens=500)
            if not _llm_usable(llm_response):
                return _sop_fallback(domain, description, action)
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
            return _sop_fallback(domain, description, action)
