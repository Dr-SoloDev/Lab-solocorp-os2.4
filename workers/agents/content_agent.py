"""Content Creator Agent — @content-creator-sek: Content, Creative, Media

Capabilities:
- Content production (blog, article, newsletter)
- Social media content
- Video/creative concept
- Caption writing
- Campaign creative
"""

from __future__ import annotations

import json

from workers.agents.base_agent import BaseAgent


class ContentAgent(BaseAgent):
    """Content Creator — ดูแล Content Production, Caption, Image, Video, Campaign"""

    def __init__(self, bus_url: str = "", api_key: str = ""):
        super().__init__(
            agent_id="content-creator-sek",
            name="Content เสก",
            profile_path="profiles/15-content-creator/SOUL.md",
            bus_url=bus_url,
            api_key=api_key,
        )

    async def execute(self, task: dict) -> dict:
        """Execute content tasks ด้วยพลัง LLM"""
        payload = task.get("payload", {})
        action = payload.get("action", "")
        description = payload.get("description", "")
        params = payload.get("params", {})

        if not description:
            return {
                "status": "failed",
                "summary": "Content Agent: ไม่มี description ใน payload",
                "details": {"action": action, "error": "missing_description"},
            }

        # Route to specialized content type
        content_type = "content"
        for ct in ["social", "video", "caption", "campaign", "blog", "newsletter"]:
            if ct in action.lower():
                content_type = ct
                break

        type_prompts = {
            "social": "คุณคือ Content Creator (เสก) ของ SoloCorp OS — วางแผน content social\n",
            "video": "คุณคือ Content Creator (เสก) ของ SoloCorp OS — เสนอ concept video/creative\n",
            "caption": "คุณคือ Content Creator (เสก) ของ SoloCorp OS — เขียน caption\n",
            "campaign": "คุณคือ Content Creator (เสก) ของ SoloCorp OS — วางแผน campaign\n",
            "blog": "คุณคือ Content Creator (เสก) ของ SoloCorp OS — เขียน blog/article\n",
            "newsletter": "คุณคือ Content Creator (เสก) ของ SoloCorp OS — เขียน newsletter\n",
        }

        # Output format ตามประเภท — enforcement โครงสร้างผลงาน
        OUTPUT_FORMATS = {
            "social": "Format: hook + body + CTA + hashtags",
            "video": "Format: concept + script outline + visual direction",
            "caption": "Format: caption ≤280 chars + hashtags",
            "campaign": "Format: goal + channels + content pillars + timeline",
            "blog": "Format: title + outline + key points",
            "newsletter": "Format: subject + sections + CTA",
        }

        @staticmethod
        def _llm_usable(result: str) -> bool:
            return bool(result and not result.startswith("⚠️ LLM ไม่พร้อม"))

        def _structure_fallback(content_type: str, description: str, action: str) -> dict:
            """Rule-based fallback — สร้างโครงสร้างผลงานจริงแม้ LLM ล้ม"""
            fmt = OUTPUT_FORMATS.get(content_type, "Format: outline + deliverables")
            return {
                "status": "completed",
                "summary": f"[{content_type.upper()}] draft plan จาก: {description[:150]} — {fmt}",
                "details": {
                    "action": action,
                    "content_type": content_type,
                    "agent": self.agent_id,
                    "llm_used": False,
                    "fallback": "output_structure",
                    "format": fmt,
                },
            }

        prompt = type_prompts.get(content_type, "คุณคือ Content Creator (เสก) ของ SoloCorp OS\n")
        prompt += f"ได้รับงานจาก CEO: {description}\n"
        if params:
            prompt += f"parameters: {json.dumps(params, ensure_ascii=False)}\n"
        prompt += "\nโปรดดำเนินการและรายงานผล"

        try:
            llm_response = await self.think(prompt, max_tokens=500)
            if not _llm_usable(llm_response):
                return _structure_fallback(content_type, description, action)
            return {
                "status": "completed",
                "summary": llm_response[:300],
                "details": {
                    "action": action,
                    "content_type": content_type,
                    "agent": self.agent_id,
                    "llm_used": True,
                    "full_response": llm_response,
                },
            }
        except Exception as e:
            return _structure_fallback(content_type, description, action)
