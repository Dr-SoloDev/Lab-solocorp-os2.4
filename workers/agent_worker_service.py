#!/usr/bin/env python3
"""
=============================================================
  🤖 SoloCorp OS — Agent Worker Service
=============================================================
  Polls Central Bus queue → Routes to Agent → Reports back

  วิธีใช้:
    python3 -m workers.agent_worker_service

  หรือรันแบบ daemon:
    nohup python3 -m workers.agent_worker_service > /tmp/agent_worker.log 2>&1 &
=============================================================
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Optional

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger("agent-worker")

# ── Add project root to path ──────────────────────────────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.agents.cfo_agent import CFOAgent
from workers.agents.architect_agent import ArchitectAgent
from workers.agents.engineering_agent import EngineeringAgent
from workers.agents.product_agent import ProductAgent
from workers.agents.orchestrator_agent import OrchestratorAgent
from workers.agents.cmo_agent import CMOAgent
from workers.agents.design_agent import DesignAgent
from workers.agents.qa_agent import QAAgent
from workers.agents.sales_agent import SalesAgent
from workers.agents.support_agent import SupportAgent
from workers.agents.legal_agent import LegalAgent
from workers.agents.web3_agent import Web3Agent
from workers.agents.content_agent import ContentAgent
from workers.agents.neteng_agent import NetEngAgent
from workers.agents.cybersec_agent import CyberSecAgent
from workers.agents.psychology_agent import PsychologyAgent
from workers.agents.ui_agent import UIAgent
from workers.agents.rd_lab_agent import RDLabAgent

from workers.evidence_collector import collect_evidence
from workers.aar_generator import generate_aar


class AgentWorkerService:
    """Agent Worker Service — หัวใจของ Agent Activation

    Architecture:
        1. Poll Central Bus queue (/v1/context สำหรับ pending tasks)
        2. Match target_agent → ส่งให้ Agent Worker ที่ถูกต้อง
        3. Agent execute task
        4. Report กลับ CEO / update queue status
    """

    def __init__(
        self,
        bus_url: str = "http://127.0.0.1:8099",
        api_key: str = "",
        poll_interval: float = 5.0,
        max_concurrent: int = 3,
    ):
        self.bus_url = bus_url.rstrip("/")
        self.api_key = api_key or os.environ.get(
            "SOLOCORP_API_KEY", "sk-solocorp-admin-local-dev-001"
        )
        self.poll_interval = poll_interval
        self.max_concurrent = max_concurrent
        self.running = False
        self._semaphore = asyncio.Semaphore(max_concurrent)

        # ── Register Agents — Phase 1 + Phase 2 ───────────────────────
        self.agents: dict[str, Any] = {
            # Phase 1 — 5 กรมหลัก
            "cfo-meetoo": CFOAgent(bus_url=bus_url, api_key=self.api_key),
            "architect-songsak": ArchitectAgent(bus_url=bus_url, api_key=self.api_key),
            "changful": EngineeringAgent(bus_url=bus_url, api_key=self.api_key),
            "product-produck": ProductAgent(bus_url=bus_url, api_key=self.api_key),
            "orchestrator-wut": OrchestratorAgent(bus_url=bus_url, api_key=self.api_key),
            # Phase 2 — การตลาด+ดีไซน์+QA+ขาย+ซัพพอร์ต
            "cmo-mark": CMOAgent(bus_url=bus_url, api_key=self.api_key),
            "design-kreet": DesignAgent(bus_url=bus_url, api_key=self.api_key),
            "qa": QAAgent(bus_url=bus_url, api_key=self.api_key),
            "sales": SalesAgent(bus_url=bus_url, api_key=self.api_key),
            "support": SupportAgent(bus_url=bus_url, api_key=self.api_key),
            # Phase 3 — กฎหมาย+Web3+คอนเทนต์+เน็ตเวิร์ค+ความปลอดภัย
            "legal-tulya": LegalAgent(bus_url=bus_url, api_key=self.api_key),
            "web3-aywa": Web3Agent(bus_url=bus_url, api_key=self.api_key),
            "content-creator-sek": ContentAgent(bus_url=bus_url, api_key=self.api_key),
            "neteng-neet": NetEngAgent(bus_url=bus_url, api_key=self.api_key),
            "cybersec-sai": CyberSecAgent(bus_url=bus_url, api_key=self.api_key),
            # Phase 4 — จิตวิทยา+UI+R&D
            "psych-jit": PsychologyAgent(bus_url=bus_url, api_key=self.api_key),
            "ui-designer": UIAgent(bus_url=bus_url, api_key=self.api_key),
            "rd-lab": RDLabAgent(bus_url=bus_url, api_key=self.api_key),
        }

        log.info(
            f"🤖 Agent Worker Service initialized with {len(self.agents)} agents"
        )

    # ── Queue Polling ──────────────────────────────────────────────────

    async def poll_queue(self) -> list[dict]:
        """Poll Central Bus for tasks ที่รอ agent ทำงาน (status=routed)"""
        try:
            from central_bus.db import ensure_db

            db = await ensure_db()
            # หา tasks ที่ target_agent เป็น agent ที่ลงทะเบียนไว้
            agent_ids = list(self.agents.keys())
            if not agent_ids:
                return []
            
            placeholders = ",".join("?" for _ in agent_ids)
            rows = await db.fetch_all(
                f"""
                SELECT * FROM queue
                WHERE status = 'routed'
                  AND target_agent IN ({placeholders})
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'normal' THEN 2
                        WHEN 'low' THEN 3
                    END,
                    created_at ASC
                LIMIT ?
                """,
                (*agent_ids, self.max_concurrent),
            )
            return [dict(r) for r in rows]
        except Exception as e:
            log.warning(f"⚠️ Queue poll failed: {e}")
            return []

    async def mark_completed(
        self, msg_id: str, result: dict, agent_id: str
    ) -> None:
        """Mark task as completed in queue"""
        try:
            from central_bus.queue import SQLiteQueueManager
            from central_bus.db import ensure_db

            db = await ensure_db()
            qm = SQLiteQueueManager(db)
            await qm.update_status(
                msg_id,
                "completed",
                result=result,
                agent_id=agent_id,
            )
        except Exception as e:
            log.error(f"❌ Failed to mark completed: {e}")

    async def _update_status(self, msg_id: str, status: str) -> None:
        """Update queue status"""
        try:
            from central_bus.queue import SQLiteQueueManager
            from central_bus.db import ensure_db
            db = await ensure_db()
            qm = SQLiteQueueManager(db)
            await db.execute(
                "UPDATE queue SET status = ?, updated_at = ? WHERE id = ?",
                (status, __import__('datetime').datetime.now().isoformat(), msg_id),
            )
        except Exception as e:
            log.warning(f"⚠️ Status update failed: {e}")

    async def mark_failed(self, msg_id: str, error: str) -> None:
        """Mark task as failed"""
        try:
            from central_bus.queue import SQLiteQueueManager
            from central_bus.db import ensure_db

            db = await ensure_db()
            qm = SQLiteQueueManager(db)
            await qm.update_status(msg_id, "failed", error=error)
        except Exception as e:
            log.error(f"❌ Failed to mark failed: {e}")

    # ── Task Processing ────────────────────────────────────────────────

    async def process_task(self, task: dict) -> None:
        """Process single task — route to agent → execute → report"""
        task_id = task.get("id", "?")
        agent_id = task.get("target_agent", "")
        source_agent = task.get("agent_id", "")
        payload_str = task.get("payload", "{}")
        payload = (
            json.loads(payload_str) if isinstance(payload_str, str) else payload_str
        )

        log.info(f"📥 Task {task_id[:8]} → {agent_id} จาก {source_agent}")

        # Find agent
        agent = self.agents.get(agent_id)
        if not agent:
            log.warning(f"⚠️ Unknown agent: {agent_id}")
            return

        try:
            start_time = time.monotonic()

            # Mark as processing
            await self._update_status(task_id, "processing")
            
            # Execute
            log.info(f"⚙️  {agent.agent_id} กำลังทำงาน...")
            result = await agent.execute(
                {
                    "task_id": task_id,
                    "source_agent": source_agent,
                    "target_agent": agent_id,
                    "payload": payload,
                    "priority": task.get("priority", "normal"),
                }
            )

            # ── Evidence & AAR (auto-collect after completion) ──
            await collect_evidence(task, result, latency_ms=int((time.monotonic() - start_time) * 1000))
            await generate_aar(task, result, start_time=start_time)

            # Mark completed
            await self.mark_completed(task_id, result, agent_id)

            # Report to CEO
            summary = result.get("summary", "ดำเนินการเสร็จสิ้น")
            await agent.report_to_ceo(
                task_id=task_id,
                status=result.get("status", "completed"),
                summary=summary,
                details=result.get("details"),
            )

            log.info(f"✅ {agent.agent_id} เสร็จ — {summary[:60]}")

        except Exception as e:
            log.error(f"❌ {agent_id} Error: {e}")
            error_result = {"status": "failed", "summary": str(e), "details": {}}
            # Still collect evidence + AAR for failed tasks
            try:
                await collect_evidence(task, error_result)
                await generate_aar(task, error_result, error=str(e))
            except Exception as nested_e:
                log.warning(f"⚠️ Failed to collect evidence for failed task: {nested_e}")
            await self.mark_failed(task_id, str(e))

    # ── Main Loop ──────────────────────────────────────────────────────

    async def run_once(self) -> int:
        """Poll + process pending tasks. Returns number processed."""
        # First clear any stale 'processing' tasks (worker crashed)
        try:
            from central_bus.db import ensure_db
            db = await ensure_db()
            await db.execute(
                "UPDATE queue SET status = 'routed' WHERE status = 'processing' AND updated_at < datetime('now', '-5 minutes')"
            )
        except: pass
        
        tasks = await self.poll_queue()
        if tasks:
            log.info(f"📬 พบ {len(tasks)} งานใน queue")

        async def _safe_process(t: dict) -> None:
            async with self._semaphore:
                await self.process_task(t)

        if tasks:
            await asyncio.gather(*[_safe_process(t) for t in tasks])

        return len(tasks)

    async def run_forever(self) -> None:
        """Run polling loop"""
        self.running = True
        log.info(
            f"🔄 Agent Worker Service started (poll every {self.poll_interval}s)"
        )
        log.info(f"   Agents: {', '.join(self.agents.keys())}")

        while self.running:
            try:
                processed = await self.run_once()
                if processed:
                    log.info(f"✅ Processed {processed} tasks this cycle")
            except Exception as e:
                log.error(f"⚠️ Cycle error: {e}")

            await asyncio.sleep(self.poll_interval)

    def stop(self) -> None:
        self.running = False


# ── CLI ──────────────────────────────────────────────────────────────

async def main():
    service = AgentWorkerService()

    # Print welcome
    print("=" * 60)
    print("  🤖 SoloCorp OS — Agent Worker Service")
    print("=" * 60)
    print(f"  Agents loaded:")
    for aid, agent in service.agents.items():
        print(f"    ✅ {aid} — {agent.get_identity_summary()}")
    print(f"  Poll interval: {service.poll_interval}s")
    print(f"  Max concurrent: {service.max_concurrent}")
    print("=" * 60)
    print()

    # Run one cycle first, then loop
    processed = await service.run_once()
    if processed:
        print(f"  ✅ Cycle 1: processed {processed} tasks")
    else:
        print("  📭 No pending tasks — waiting...")

    await service.run_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("🛑 Agent Worker Service stopped")
        print("\n🛑 Agent Worker Service stopped")
