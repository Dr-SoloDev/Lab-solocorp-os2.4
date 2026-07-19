#!/usr/bin/env python3
"""Central Bus v0.6 — Behavior Taxonomy Migration.

Seeds 26 behaviors into ``behavior_taxonomy`` and ``behavior_route_map``.

Usage::

    # Validate only (dry run)
    python -m central_bus.behavior_migration --dry-run

    # Apply migration
    python -m central_bus.behavior_migration

    # Verbose
    python -m central_bus.behavior_migration --verbose

Design
~~~~~~
26 behaviours organised across 17 domains, covering all 18 SoloCorp departments.
Each behavior has:
  - A unique ``behavior_name`` (snake_case)
  - ``keywords`` for classifier training (JSON array)
  - ``confidence_threshold`` — >=0.9 auto-route, <0.9 -> CEO review
  - ``routing_logic`` — direct | orchestrator | ceo_review | round_robin

Migration Strategy
~~~~~~~~~~~~~~~~~~
- Add-on (non-destructive): existing keyword routing (Tier 1) untouched.
- Behavior layer sits BEFORE Tier 1 keyword matching.
- Idempotent: safe to re-run (checks schema_migrations before insert).

References
~~~~~~~~~~
- CEO Order: 2026-07-20 — Behavior-Centric Routing: Execute
- ADR-{next}: Behavior-Centric Routing Architecture
"""

from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import logging
import sys
import uuid
from datetime import datetime, timezone
from typing import Any

from central_bus.db import DbManager

log = logging.getLogger(__name__)

MIGRATION_NAME = "v001_seed_26_behaviors"
MIGRATION_DESC = "Seed 26 behavior intents + route map for Behavior-Centric Routing"


def _j(data: list[str]) -> str:
    """Shortcut: list[str] -> JSON array string."""
    return json.dumps(data, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════════════
# 26 Behaviors — Seed Data
# ═══════════════════════════════════════════════════════════════════════
# Organised by domain. Each entry:
#   keywords:    JSON string of trigger phrases for classifier training
#   threshold:   confidence threshold (0.0-1.0)
# ═══════════════════════════════════════════════════════════════════════

BEHAVIORS: list[dict[str, Any]] = [
    # ── Leadership (CEO) ──────────────────────────────────────────
    {
        "domain": "leadership",
        "behavior_name": "vision_strategy",
        "description": "กำหนดวิสัยทัศน์ กลยุทธ์ ทิศทางองค์กร — vision, mission, strategic direction",
        "keywords": _j(["vision", "strategy", "mission", "direction", "goal", "objective", "กลยุทธ์", "วิสัยทัศน์", "เป้าหมาย", "ทิศทาง"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "leadership",
        "behavior_name": "owner_decision",
        "description": "การตัดสินใจระดับสูง — final call, escalation, approval gate, executive decision",
        "keywords": _j(["final decision", "approve", "escalate", "owner decision", "executive", "decide", "อนุมัติ", "ตัดสินใจ", "owner"]),
        "confidence_threshold": 0.95,
        "is_active": 1,
    },
    # ── Finance (CFO) ────────────────────────────────────────────
    {
        "domain": "finance",
        "behavior_name": "budget_approval",
        "description": "อนุมัติงบประมาณ จัดสรรทรัพยากรทางการเงิน — budget planning, resource allocation",
        "keywords": _j(["budget", "approve budget", "funding", "allocate", "resource", "งบประมาณ", "งบ", "จัดสรร", "ทุน"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "finance",
        "behavior_name": "cost_analysis",
        "description": "วิเคราะห์ต้นทุน ROI financial modeling — cost, profit, investment analysis",
        "keywords": _j(["cost", "roi", "profit", "revenue", "financial model", "forecast", "ต้นทุน", "กำไร", "รายได้", "วิเคราะห์การเงิน"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Marketing (CMO) ─────────────────────────────────────────
    {
        "domain": "marketing",
        "behavior_name": "campaign_management",
        "description": "วางแผนแคมเปญ ดำเนินการวัดผล — campaign planning, execution, measurement",
        "keywords": _j(["campaign", "marketing", "promotion", "advertise", "แคมเปญ", "การตลาด", "โปรโมท", "โฆษณา"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "marketing",
        "behavior_name": "brand_strategy",
        "description": "กำหนดแบรนด์ positioning เอกลักษณ์ — brand identity, positioning, messaging",
        "keywords": _j(["brand", "positioning", "brand identity", "messaging", "แบรนด์", "เอกลักษณ์"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Content (Content Creator) ────────────────────────────────
    {
        "domain": "content",
        "behavior_name": "content_production",
        "description": "สร้างเนื้อหา caption video copy — content creation, copywriting, media production",
        "keywords": _j(["content", "write", "caption", "copy", "video", "script", "คอนเทนต์", "เขียน", "แคปชั่น", "บทความ"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Operations (Orchestrator) ─────────────────────────────────
    {
        "domain": "operations",
        "behavior_name": "pipeline_coordination",
        "description": "ประสานงานข้ามแผนก จัดการ workflow — cross-dept coordination, workflow orchestration",
        "keywords": _j(["pipeline", "workflow", "orchestrate", "coordinate", "cross", "handoff", "pipeline status", "ประสานงาน", "ส่งต่อ"]),
        "confidence_threshold": 0.85,
        "is_active": 1,
    },
    # ── Architecture (Architect) ──────────────────────────────────
    {
        "domain": "architecture",
        "behavior_name": "architecture_design",
        "description": "ออกแบบระบบ bus schema — system design, central bus, architecture decision",
        "keywords": _j(["architecture", "system design", "schema", "central bus", "architecture decision", "adr", "สถาปัตยกรรม", "ออกแบบระบบ"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "architecture",
        "behavior_name": "routing_monitoring",
        "description": "ตั้งค่า routing เฝ้าระบบ — routing rules, monitoring, circuit breaker, health check",
        "keywords": _j(["routing", "route", "monitor", "health check", "watchdog", "circuit breaker", "เส้นทาง", "มอนิเตอร์", "เฝ้าระวัง"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Product (Product) ─────────────────────────────────────────
    {
        "domain": "product",
        "behavior_name": "feature_definition",
        "description": "กำหนด features PRD requirements — feature spec, product requirements, user stories",
        "keywords": _j(["feature", "prd", "requirement", "user story", "product", "spec", "feature request", "ฟีเจอร์", "ความต้องการ"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "product",
        "behavior_name": "roadmap_planning",
        "description": "วางแผน roadmap จัดลำดับความสำคัญ — prioritization, release planning, backlog",
        "keywords": _j(["roadmap", "prioritize", "backlog", "release", "planning", "sprint", "โรดแมพ", "ลำดับความสำคัญ"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Engineering (Engineering) ─────────────────────────────────
    {
        "domain": "engineering",
        "behavior_name": "backend_development",
        "description": "พัฒนา backend API database — server-side, API, database, microservice",
        "keywords": _j(["backend", "api", "database", "server", "microservice", "endpoint", "แบ็กเอนด์", "ฐานข้อมูล", "เซิร์ฟเวอร์"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "engineering",
        "behavior_name": "frontend_development",
        "description": "พัฒนา frontend UI component — client-side, UI code, Tailwind, React, Vue",
        "keywords": _j(["frontend", "ui code", "component", "tailwind", "react", "vue", "html", "css", "ui component"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "engineering",
        "behavior_name": "bug_fixing",
        "description": "แก้บั๊ก ซ่อมระบบ debug — bug report, defect, fix, error, regression",
        "keywords": _j(["bug", "fix", "error", "crash", "defect", "regression", "broken", "บั๊ก", "แก้", "พัง"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Design & UI (Design / UI Designer) ───────────────────────
    {
        "domain": "design",
        "behavior_name": "visual_design",
        "description": "ออกแบบ visual design system — design system, visual identity, brand visual, component library",
        "keywords": _j(["design system", "visual", "component library", "style guide", "figma", "ออกแบบ", "component"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "design",
        "behavior_name": "ux_research",
        "description": "วิจัย UX wireframe — user research, usability, wireframe, information architecture",
        "keywords": _j(["ux", "user research", "usability", "wireframe", "user experience", "research", "ux research", "วิจัย", "ผู้ใช้"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Quality (QA) ───────────────────────────────────────────────
    {
        "domain": "quality",
        "behavior_name": "qa_testing",
        "description": "ทดสอบ ตรวจสอบคุณภาพ — testing, QA, test case, automation test, quality check",
        "keywords": _j(["test", "qa", "quality", "test case", "automation test", "testing", "ทดสอบ", "คุณภาพ"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Sales (Sales) ─────────────────────────────────────────────
    {
        "domain": "sales",
        "behavior_name": "sales_deal",
        "description": "จัดการดีล ขาย proposal — deal management, sales pipeline, proposal, closing",
        "keywords": _j(["sales", "deal", "proposal", "pipeline deal", "close", "prospect", "ขาย", "ดีล", "เซลส์"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Support (Support) ─────────────────────────────────────────
    {
        "domain": "support",
        "behavior_name": "customer_support",
        "description": "ให้บริการลูกค้า ticket — customer service, ticket, issue resolution, help",
        "keywords": _j(["support", "customer", "ticket", "help", "issue", "service", "ซัพพอร์ต", "ลูกค้า", "ช่วย"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Legal (Legal) ─────────────────────────────────────────────
    {
        "domain": "legal",
        "behavior_name": "legal_compliance",
        "description": "ติดตาม compliance กฎระเบียบ — regulatory compliance, PDPA, GDPR, audit readiness",
        "keywords": _j(["compliance", "regulatory", "pdpa", "gdpr", "regulation", "กฎหมาย", "compliant", "ปฏิบัติตาม"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    {
        "domain": "legal",
        "behavior_name": "contract_management",
        "description": "จัดการสัญญา นิติกรรม — contract review, agreement, NDA, MOU, legal document",
        "keywords": _j(["contract", "agreement", "nda", "mou", "legal", "document", "สัญญา", "นิติกรรม", "ข้อตกลง"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Web3 (Web3) ───────────────────────────────────────────────
    {
        "domain": "web3",
        "behavior_name": "smart_contract_defi",
        "description": "พัฒนา smart contract DeFi Solana — blockchain, Solidity, Anchor, tokenomics",
        "keywords": _j(["smart contract", "defi", "solana", "blockchain", "solidity", "anchor", "token", "crypto", "web3"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Network (NetEng) ──────────────────────────────────────────
    {
        "domain": "network",
        "behavior_name": "network_operations",
        "description": "จัดการเครือข่าย CDN DNS VPN — network infrastructure, load balancing, connectivity",
        "keywords": _j(["network", "cdn", "dns", "vpn", "load balancer", "bandwidth", "network infra", "เครือข่าย"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Security (CyberSec) ──────────────────────────────────────
    {
        "domain": "security",
        "behavior_name": "security_incident",
        "description": "จัดการภัยคุกคามความปลอดภัย — threat detection, vulnerability, incident response",
        "keywords": _j(["security", "threat", "vulnerability", "incident", "breach", "attack", "cyber", "ความปลอดภัย", "ภัยคุกคาม"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
    # ── Psychology (Psychology) ───────────────────────────────────
    {
        "domain": "psychology",
        "behavior_name": "behavioral_research",
        "description": "วิเคราะห์พฤติกรรม จิตวิทยา — user behavior, cognitive bias, behavioral economics",
        "keywords": _j(["psychology", "behavior", "cognitive bias", "user behavior", "behavioral", "จิตวิทยา", "พฤติกรรม", "bias"]),
        "confidence_threshold": 0.9,
        "is_active": 1,
    },
]

# ═══════════════════════════════════════════════════════════════════════
# Behavior -> Department Route Map
# ═══════════════════════════════════════════════════════════════════════
# Maps each behavior_name to:
#   primary_dept:     main department that handles this intent
#   secondary_depts:  fallback depts when primary isn't available
#   routing_logic:    "direct" | "orchestrator" | "ceo_review" | "round_robin"
#   priority_boost:   0=normal, 1=high, 2=critical
# ═══════════════════════════════════════════════════════════════════════

ROUTE_MAP: dict[str, dict[str, Any]] = {
    # ── Leadership ────────────────────────────────────────────────
    "vision_strategy": {
        "primary_dept": "ceo",
        "secondary_depts": _j(["architect"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    "owner_decision": {
        "primary_dept": "ceo",
        "secondary_depts": _j(["orchestrator"]),
        "routing_logic": "ceo_review",
        "priority_boost": 2,
    },
    # ── Finance ───────────────────────────────────────────────────
    "budget_approval": {
        "primary_dept": "cfo",
        "secondary_depts": _j(["ceo"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    "cost_analysis": {
        "primary_dept": "cfo",
        "secondary_depts": _j(["ceo"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    # ── Marketing ─────────────────────────────────────────────────
    "campaign_management": {
        "primary_dept": "cmo",
        "secondary_depts": _j(["content_creator", "design"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    "brand_strategy": {
        "primary_dept": "cmo",
        "secondary_depts": _j(["design"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    # ── Content ───────────────────────────────────────────────────
    "content_production": {
        "primary_dept": "content_creator",
        "secondary_depts": _j(["cmo"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    # ── Operations ────────────────────────────────────────────────
    "pipeline_coordination": {
        "primary_dept": "orchestrator",
        "secondary_depts": _j(["architect"]),
        "routing_logic": "orchestrator",
        "priority_boost": 1,
    },
    # ── Architecture ──────────────────────────────────────────────
    "architecture_design": {
        "primary_dept": "architect",
        "secondary_depts": _j(["engineering", "orchestrator"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    "routing_monitoring": {
        "primary_dept": "architect",
        "secondary_depts": _j(["orchestrator"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    # ── Product ───────────────────────────────────────────────────
    "feature_definition": {
        "primary_dept": "product",
        "secondary_depts": _j(["engineering", "design"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    "roadmap_planning": {
        "primary_dept": "product",
        "secondary_depts": _j(["ceo", "engineering"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    # ── Engineering ───────────────────────────────────────────────
    "backend_development": {
        "primary_dept": "engineering",
        "secondary_depts": _j(["architect"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    "frontend_development": {
        "primary_dept": "engineering",
        "secondary_depts": _j(["ui_designer", "design"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    "bug_fixing": {
        "primary_dept": "engineering",
        "secondary_depts": _j(["qa"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    # ── Design ───────────────────────────────────────────────────
    "visual_design": {
        "primary_dept": "design",
        "secondary_depts": _j(["ui_designer"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    "ux_research": {
        "primary_dept": "design",
        "secondary_depts": _j(["product", "psychology"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    # ── Quality ───────────────────────────────────────────────────
    "qa_testing": {
        "primary_dept": "qa",
        "secondary_depts": _j(["engineering"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    # ── Sales ────────────────────────────────────────────────────
    "sales_deal": {
        "primary_dept": "sales",
        "secondary_depts": _j(["cmo"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    # ── Support ──────────────────────────────────────────────────
    "customer_support": {
        "primary_dept": "support",
        "secondary_depts": _j(["engineering", "sales"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    # ── Legal ────────────────────────────────────────────────────
    "legal_compliance": {
        "primary_dept": "legal",
        "secondary_depts": _j(["ceo"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    "contract_management": {
        "primary_dept": "legal",
        "secondary_depts": _j(["cfo"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    # ── Web3 ─────────────────────────────────────────────────────
    "smart_contract_defi": {
        "primary_dept": "web3",
        "secondary_depts": _j(["engineering", "legal"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
    # ── Network ──────────────────────────────────────────────────
    "network_operations": {
        "primary_dept": "neteng",
        "secondary_depts": _j(["architect"]),
        "routing_logic": "direct",
        "priority_boost": 1,
    },
    # ── Security ─────────────────────────────────────────────────
    "security_incident": {
        "primary_dept": "cybersec",
        "secondary_depts": _j(["architect", "engineering"]),
        "routing_logic": "direct",
        "priority_boost": 2,
    },
    # ── Psychology ───────────────────────────────────────────────
    "behavioral_research": {
        "primary_dept": "psychology",
        "secondary_depts": _j(["design", "product"]),
        "routing_logic": "direct",
        "priority_boost": 0,
    },
}


# ═══════════════════════════════════════════════════════════════════════
# Migration Engine
# ═══════════════════════════════════════════════════════════════════════

def _new_id() -> str:
    return str(uuid.uuid4())


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _checksum(data: list[dict[str, Any]]) -> str:
    """Compute checksum of seed data to detect changes."""
    raw = json.dumps(data, sort_keys=True, ensure_ascii=False).encode()
    return hashlib.sha256(raw).hexdigest()[:16]


class BehaviorMigration:
    """Seed behavior_taxonomy + behavior_route_map tables."""

    def __init__(self, db: DbManager, dry_run: bool = False) -> None:
        self._db = db
        self.dry_run = dry_run
        self.stats: dict[str, int] = {
            "behaviors_inserted": 0,
            "behaviors_skipped": 0,
            "routes_inserted": 0,
            "routes_skipped": 0,
        }

    async def _is_already_applied(self) -> bool:
        """Check if this migration has already been applied."""
        row = await self._db.fetch_one(
            "SELECT id FROM schema_migrations WHERE name = ?",
            (MIGRATION_NAME,),
        )
        return row is not None

    async def _record_migration(self) -> None:
        """Record this migration in schema_migrations."""
        if self.dry_run:
            return
        chk = _checksum(BEHAVIORS)
        await self._db.execute(
            """
            INSERT OR IGNORE INTO schema_migrations (id, name, checksum, description)
            VALUES (?, ?, ?, ?)
            """,
            (_new_id(), MIGRATION_NAME, chk, MIGRATION_DESC),
        )

    async def _seed_behaviors(self) -> None:
        """Insert 26 behaviors into behavior_taxonomy."""
        log.info("Seeding %d behaviors...", len(BEHAVIORS))

        # Check which behaviors already exist
        existing_rows = await self._db.fetch_all(
            "SELECT behavior_name FROM behavior_taxonomy"
        )
        existing_names = {r["behavior_name"] for r in existing_rows}

        for bhv in BEHAVIORS:
            if bhv["behavior_name"] in existing_names:
                self.stats["behaviors_skipped"] += 1
                continue

            if not self.dry_run:
                await self._db.execute(
                    """
                    INSERT INTO behavior_taxonomy
                        (id, domain, behavior_name, description, keywords,
                         confidence_threshold, is_active, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        _new_id(),
                        bhv["domain"],
                        bhv["behavior_name"],
                        bhv["description"],
                        bhv["keywords"],
                        bhv["confidence_threshold"],
                        bhv["is_active"],
                        _now_iso(),
                        _now_iso(),
                    ),
                )
            self.stats["behaviors_inserted"] += 1

    async def _seed_route_map(self) -> None:
        """Insert behavior -> department routes into behavior_route_map."""
        # Fetch all behavior IDs
        behavior_rows = await self._db.fetch_all(
            "SELECT id, behavior_name FROM behavior_taxonomy"
        )
        behavior_map: dict[str, str] = {
            r["behavior_name"]: r["id"] for r in behavior_rows
        }

        # Check existing route map entries
        existing_rows = await self._db.fetch_all(
            "SELECT behavior_id FROM behavior_route_map"
        )
        existing_behavior_ids = {r["behavior_id"] for r in existing_rows}

        for bname, route in ROUTE_MAP.items():
            bhv_id = behavior_map.get(bname)
            if not bhv_id:
                log.warning("Behavior '%s' not found in taxonomy — skipping route", bname)
                continue

            if bhv_id in existing_behavior_ids:
                self.stats["routes_skipped"] += 1
                continue

            if not self.dry_run:
                await self._db.execute(
                    """
                    INSERT INTO behavior_route_map
                        (id, behavior_id, primary_dept, secondary_depts,
                         routing_logic, priority_boost, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        _new_id(),
                        bhv_id,
                        route["primary_dept"],
                        route["secondary_depts"],
                        route["routing_logic"],
                        route["priority_boost"],
                        _now_iso(),
                        _now_iso(),
                    ),
                )
            self.stats["routes_inserted"] += 1

    async def verify(self) -> bool:
        """Verify seed counts. Returns True if all checks pass."""
        log.info("=" * 50)
        log.info("Verification")
        log.info("=" * 50)

        all_ok = True

        # Check behavior count
        bhv_count = (await self._db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM behavior_taxonomy"
        ))["cnt"]
        log.info("Behavior Taxonomy: %d rows (expected %d)", bhv_count, len(BEHAVIORS))
        if bhv_count < len(BEHAVIORS):
            log.warning("Some behaviors missing: %d < %d", bhv_count, len(BEHAVIORS))
            all_ok = False

        # Check route map count
        route_count = (await self._db.fetch_one(
            "SELECT COUNT(*) AS cnt FROM behavior_route_map"
        ))["cnt"]
        log.info("Behavior Route Map:  %d rows (expected %d)", route_count, len(ROUTE_MAP))
        if route_count < len(ROUTE_MAP):
            log.warning("Some routes missing: %d < %d", route_count, len(ROUTE_MAP))
            all_ok = False

        # Show domain breakdown
        domains = await self._db.fetch_all(
            "SELECT domain, COUNT(*) AS cnt FROM behavior_taxonomy GROUP BY domain ORDER BY domain"
        )
        log.info("Domain Breakdown:")
        for d in domains:
            log.info("  %-20s %2d behaviors", d["domain"], d["cnt"])

        # Check migration record
        mig = await self._db.fetch_one(
            "SELECT name, checksum, applied_at FROM schema_migrations WHERE name = ?",
            (MIGRATION_NAME,),
        )
        if mig:
            log.info("Migration record: %s (checksum: %s, applied: %s)",
                     mig["name"], mig["checksum"], mig["applied_at"])
        else:
            log.warning("No migration record found (dry run or not applied)")

        if all_ok:
            log.info("All seeds verified!")
        else:
            log.warning("Some counts mismatch — investigate before cutover")

        return all_ok

    async def run(self) -> bool:
        """Run the full migration. Returns True if successful."""
        log.info("Behavior Migration %s", "(DRY RUN — no writes)" if self.dry_run else "")

        # Check if already applied
        if not self.dry_run:
            already = await self._is_already_applied()
            if already:
                log.info("Migration '%s' already applied — skipping", MIGRATION_NAME)
                log.info("Use --force to re-run (not recommended)")
                return True

        log.info("-" * 50)

        await self._seed_behaviors()
        await self._seed_route_map()
        if not self.dry_run:
            await self._record_migration()

        log.info("-" * 50)
        log.info(
            "Stats: %d behaviors inserted, %d skipped | %d routes inserted, %d skipped",
            self.stats["behaviors_inserted"],
            self.stats["behaviors_skipped"],
            self.stats["routes_inserted"],
            self.stats["routes_skipped"],
        )

        if not self.dry_run:
            return await self.verify()
        return True


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Central Bus v0.6 — Behavior Taxonomy Migration",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate only — no database writes",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable debug logging",
    )
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    db = DbManager()
    await db.init()

    engine = BehaviorMigration(db, dry_run=args.dry_run)
    success = await engine.run()

    await db.close()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(_main())
