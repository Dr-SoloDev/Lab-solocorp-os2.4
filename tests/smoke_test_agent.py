"""Smoke test pipeline — 3 automated prompts against any Department Head profile.

Run with:
    # Test default (QA) profile
    pytest tests/smoke_test_agent.py

    # Test specific profile
    PROFILE_PATH=profiles/05-architect/SOUL.md pytest tests/smoke_test_agent.py

    # Filter one test type
    pytest tests/smoke_test_agent.py -k domain

Integration: called automatically after `/deploy` to verify active profiles.
"""

from __future__ import annotations

import os
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

import pytest

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from workers.llm_provider import think as llm_think


# ── Profile domain map ─────────────────────────────────────────────────────

DOMAIN_KEYWORDS: dict[str, dict[str, Any]] = {
    "01-ceo": {
        "domain": "Company Strategy & Leadership",
        "terms": ["strategy", "vision", "resource", "decision", "direction", "alignment", "กลยุทธ", "วิสัยทัศน์", "ตัดสินใจ", "ทิศทาง", "ทรัพยากร"],
    },
    "02-cfo": {
        "domain": "Finance & Budget",
        "terms": ["budget", "ROI", "cost", "revenue", "forecast", "financial", "investment", "งบประมาณ", "การเงิน", "ต้นทุน", "รายได้", "ลงทุน"],
    },
    "03-cmo": {
        "domain": "Marketing & Brand",
        "terms": ["brand", "campaign", "marketing", "audience", "engagement", "positioning", "แบรนด์", "การตลาด", "แคมเปญ", "กลุ่มเป้าหมาย"],
    },
    "04-orchestrator": {
        "domain": "Orchestration & Workflow",
        "terms": ["pipeline", "workflow", "handoff", "coordination", "timeline", "dependencies", "ประสาน", "ส่งต่อ", "ลำดับ", "流程", "ขั้นตอน"],
    },
    "05-architect": {
        "domain": "System Architecture",
        "terms": ["architecture", "pipeline", "infrastructure", "scal", "design", "system", "สถาปัตย", "โครงสร้าง", "ระบบ", "ออกแบบ"],
    },
    "06-product": {
        "domain": "Product Management",
        "terms": ["product", "roadmap", "feature", "user", "backlog", "PRD", "ผลิตภัณฑ์", "ฟีเจอร์", "ผู้ใช้", "ความต้องการ"],
    },
    "07-engineering": {
        "domain": "Software Engineering",
        "terms": ["code", "test", "deploy", "review", "refactor", "technical", "พัฒนา", "โค้ด", "ปรับปรุง", "แก้ไข"],
    },
    "08-design": {
        "domain": "Design System",
        "terms": ["design", "component", "prototype", "user", "interface", "brand", "ดีไซน์", "ส่วนประกอบ", "ต้นแบบ", "ประสบการณ์"],
    },
    "09-ui-designer": {
        "domain": "UI/UX Design",
        "terms": ["user", "flow", "interface", "mobile", "click", "ux", "ผู้ใช้", "หน้าจอ", "交互", "อินเทอร์เฟซ"],
    },
    "10-qa": {
        "domain": "Quality Assurance",
        "terms": ["test", "bug", "regression", "quality", "automation", "release", "ทดสอบ", "บัก", "คุณภาพ", "ตรวจสอบ", "ข้อผิดพลาด"],
    },
    "11-sales": {
        "domain": "Sales & Business Development",
        "terms": ["sales", "client", "pipeline", "deal", "revenue", "relationship", "ขาย", "ลูกค้า", "ดีล", "รายได้", "โอกาส"],
    },
    "12-support": {
        "domain": "Customer Support",
        "terms": ["support", "customer", "ticket", "response", "SLA", "resolution", "สนับสนุน", "ลูกค้า", "ช่วยเหลือ", "แก้ไข", "ปัญหา"],
    },
    "13-legal": {
        "domain": "Legal & Compliance",
        "terms": ["compliance", "legal", "risk", "policy", "regulatory", "contract", "กฎหมาย", "ปฏิบัติตาม", "ความเสี่ยง", "สัญญา", "ข้อกำหนด"],
    },
    "14-web3": {
        "domain": "Web3 & Blockchain",
        "terms": ["blockchain", "smart contract", "decentralized", "token", "defi", "wallet", "บล็อคเชน", "สัญญาอัจฉริยะ", "โทเค็น"],
    },
    "15-content-creator": {
        "domain": "Content Creation",
        "terms": ["content", "blog", "social", "audience", "engage", "copy", "เนื้อหา", "คอนเทนต์", "โซเชียล", "เขียน", "สื่อ"],
    },
    "16-neteng": {
        "domain": "Network Engineering",
        "terms": ["network", "latency", "bandwidth", "infrastructure", "connect", "monitor", "เครือข่าย", "เน็ตเวิร์ค", "เชื่อมต่อ", " monitoring"],
    },
    "17-cybersec": {
        "domain": "Cybersecurity",
        "terms": ["security", "threat", "vulnerability", "risk", "incident", "protect", "ความปลอดภัย", "ภัยคุกคาม", "ช่องโหว่", "ป้องกัน"],
    },
    "18-psychology": {
        "domain": "Psychology & Human Factors",
        "terms": ["behavior", "cognitive", "user", "emotion", "trust", "motivation", "จิตวิทยา", "พฤติกรรม", "อารมณ์", "แรงจูงใจ", "ความคิด"],
    },
    "19-rd-lab": {
        "domain": "R&D / Research Lab",
        "terms": ["research", "experiment", "prototype", "innovation", "explore", "frontier", "วิจัย", "ทดลอง", "ต้นแบบ", "นวัตกรรม", "สำรวจ"],
    },
}


# ── Fixtures ───────────────────────────────────────────────────────────────


def _default_profile() -> Path:
    return _project_root / "profiles" / "10-qa" / "SOUL.md"


@pytest.fixture(scope="session")
def profile_path() -> Path:
    """Profile path from env var PROFILE_PATH, or default QA profile."""
    env_path = os.environ.get("PROFILE_PATH")
    if env_path:
        p = Path(env_path)
        if not p.is_absolute():
            p = _project_root / p
        if not p.exists():
            pytest.skip(f"PROFILE_PATH not found: {p}")
        return p.resolve()
    return _default_profile()


@pytest.fixture(scope="session")
def profile_name(profile_path: Path) -> str:
    """Directory name of the profile (e.g. '10-qa')."""
    return profile_path.parent.name


@pytest.fixture(scope="session")
def soul_content(profile_path: Path) -> str:
    text = profile_path.read_text(encoding="utf-8")
    if not text.strip():
        pytest.skip(f"Empty SOUL.md: {profile_path}")
    return text


@pytest.fixture(scope="session")
def domain_info(profile_name: str) -> dict[str, Any]:
    """Lookup domain keywords for this profile, or derive generically."""
    info = DOMAIN_KEYWORDS.get(profile_name)
    if info is None:
        info = {
            "domain": "General",
            "terms": ["solocorp", "team", "org", "work", "system", "process"],
        }
    return info


# ── Helpers ────────────────────────────────────────────────────────────────


def extract_title(soul: str) -> str:
    """Extract the first H1 as the agent's title."""
    m = re.search(r"^# (.+)", soul, re.MULTILINE)
    return m.group(1).strip() if m else "Unknown Agent"


def extract_role(soul: str) -> str:
    """Extract the role/position from the Identity section."""
    m = re.search(r"\*\*ตำแหน่ง:\*\* (.+)", soul)
    if m:
        return m.group(1).strip()
    m2 = re.search(r"\*\*ตำแหน่ง\*\*[|](.+)", soul)
    return m2.group(1).strip() if m2 else ""


def extract_rules(soul: str) -> list[str]:
    """Extract numbered rules from the profile."""
    rules = re.findall(r"^\d+\.\s+(.+)", soul, re.MULTILINE)
    return [r.strip() for r in rules if r.strip()]


def build_system_prompt(soul: str, pname: str) -> str:
    """Build a concise system prompt from the SOUL.md content."""
    title = extract_title(soul)
    role = extract_role(soul)
    rules = extract_rules(soul)
    rules_text = "\n".join(f"- {r}" for r in rules[:5])

    return (
        f"คุณคือ {title}\n"
        f"บทบาท: {role}\n"
        f"--- กฎ ---\n{rules_text}\n\n"
        f"ตอบเป็นภาษาไทย กระชับ ใช้ข้อมูลจากบทบาทตัวเอง\n"
        f"อย่าใช้ markdown หรือ emoji เกินจำเป็น"
    )


async def call_agent(soul: str, pname: str, prompt: str) -> str:
    """Call the LLM via workers/llm_provider with the SOUL context."""
    system = build_system_prompt(soul, pname)
    return await llm_think(prompt=prompt, system_prompt=system)


def count_matches(response: str, keywords: list[str]) -> int:
    """Count how many keywords appear in the response (case-insensitive)."""
    lower = response.lower()
    return sum(1 for kw in keywords if kw.lower() in lower)


def fuzzy_match_domain(response: str, keywords: list[str], threshold: float = 0.5) -> bool:
    """Check if response mentions domain-relevant topics using fuzzy matching."""
    resp_lower = response.lower()
    resp_words = re.findall(r'\w+', resp_lower)

    for kw in keywords:
        kw_lower = kw.lower()
        if kw_lower in resp_lower:
            return True
        for rw in resp_words:
            if SequenceMatcher(None, kw_lower, rw).ratio() >= threshold:
                return True
    return False


UNCERTAINTY_PHRASES = [
    "ฉันไม่แน่ใจ", "ไม่รู้", "ไม่ทราบ", "ไม่แน่ใจ",
    "I'm not sure", "I don't know", "I'm not certain",
    "ไม่มั่นใจ", "น่าจะ", "ขอโทษ", "ไม่สามารถตอบ",
]


# ── Test: Domain Question ────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_domain_question(
    soul_content: str,
    profile_name: str,
    domain_info: dict[str, Any],
) -> None:
    """Ask a domain-relevant question; verify the response uses domain terms."""
    domain = domain_info["domain"]
    terms = domain_info["terms"]

    prompt = (
        f"ในฐานะ Head of {domain} ของ SoloCorp OS "
        f"คุณเห็น pain point อะไรในระบบปัจจุบันบ้าง "
        f"และมีแนวทางแก้ไขอย่างไร?"
    )

    response = await call_agent(soul_content, profile_name, prompt)

    assert response, "Response should not be empty"
    assert "⚠️" not in response, f"LLM unavailable: {response}"

    # Check response is substantive
    assert len(response) > 50, f"Response too short/empty: {response[:100]}"

    # Check response is not generic filler
    has_uncertainty = any(p in response.lower() for p in UNCERTAINTY_PHRASES)
    assert not has_uncertainty, f"Response shows uncertainty/refusal: {response[:200]}"

    # Fuzzy domain relevance check (instead of rigid keyword counting)
    is_relevant = fuzzy_match_domain(response, terms)
    assert is_relevant, (
        f"No domain-relevant content detected in response. "
        f"Domain: {domain}\n"
        f"Response: {response[:300]}"
    )


# ── Test: Pushback Scenario ──────────────────────────────────────────────


@pytest.mark.asyncio
async def test_pushback_scenario(
    soul_content: str,
    profile_name: str,
    domain_info: dict[str, Any],
) -> None:
    """Challenge the agent's approach; verify they hold ground in-character."""
    domain = domain_info["domain"]
    rules = extract_rules(soul_content)

    challenge = (
        f"ฉันว่า {domain} ของคุณมันใช้ไม่ได้ผล "
        f"เราควรลดความสำคัญของ {domain} ลง "
        f"แล้ว focus ที่อย่างอื่นก่อนดีกว่า"
    )

    prompt = (
        f"เพื่อนร่วมทีมบอกคุณว่า:\n\n"
        f'"{challenge}"\n\n'
        f"คุณจะตอบกลับอย่างไร?"
    )

    response = await call_agent(soul_content, profile_name, prompt)

    assert response, "Response should not be empty"
    assert "⚠️" not in response, f"LLM unavailable: {response}"

    negative_indicators = ["คุณพูดถูก", "ok", "ก็ได้", "ใช่เลย", "you're right", "i agree"]
    has_rolled_over = any(ind in response.lower() for ind in negative_indicators)

    assert not has_rolled_over, (
        f"Agent rolled over to pushback instead of holding ground. "
        f"Response: {response[:300]}"
    )

    if rules:
        pushback_indicators = ["ไม่", "วัด", "ข้อมูล", "หลักฐาน", "scope"]
        reasoning_patterns = [
            "เพราะ", "เหตุผล", "ควร", "ต้อง", "สำคัญ",
            "จำเป็น", "ถ้า", "แต่", "อย่างไร", "แนะนำ",
            "ขอ", "อธิบาย", "เหตุ", "ผล", "เนื่องจาก",
        ]

        has_rule_keyword = any(
            any(word.strip("*:").lower() in response.lower() for word in rule.lower().split()[:3])
            for rule in rules[:3]
        )
        has_pushback = any(ind in response.lower() for ind in pushback_indicators)
        has_reasoning = any(pat in response.lower() for pat in reasoning_patterns)

        assert has_rule_keyword or (has_pushback and has_reasoning), (
            f"Response should push back on the challenge. "
            f"Rules: {rules[:3]}\n"
            f"Response: {response[:300]}"
        )


# ── Test: Out-of-Scope ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_out_of_scope(
    soul_content: str,
    profile_name: str,
) -> None:
    """Ask something outside the agent's domain; verify they deflect in-character."""
    irrelevant_questions = {
        "01-ceo": "ช่วยคิดแคมเปญการตลาด TikTok ให้หน่อย",
        "02-cfo": "ช่วยออกแบบ UI หน้า dashboard ให้หน่อย",
        "03-cmo": "ช่วย audit smart contract ให้หน่อย",
        "04-orchestrator": "ช่วยเขียน test cases สำหรับ regression testing",
        "05-architect": "ช่วยเขียน copy สำหรับ social media post",
        "06-product": "ช่วย configure firewall ให้หน่อย",
        "07-engineering": "ช่วยออกแบบ brand guideline",
        "08-design": "ช่วยคำนวณ ROI ของโปรเจกต์นี้",
        "09-ui-designer": "ช่วยเขียน test plan สำหรับ release",
        "10-qa": "ช่วยออกแบบ architecture ของระบบใหม่",
        "11-sales": "ช่วย debug production incident",
        "12-support": "ช่วยออกแบบ tokenomics",
        "13-legal": "ช่วยเขียน campaign brief",
        "14-web3": "ช่วยร่างสัญญาจ้างงาน",
        "15-content-creator": "ช่วยวิเคราะห์ network latency",
        "16-neteng": "ช่วยทำ A/B test copy",
        "17-cybersec": "ช่วย design system component library",
        "18-psychology": "ช่วย deploy smart contract",
        "19-rd-lab": "ช่วยจัดทำ sales forecast",
    }

    question = irrelevant_questions.get(
        profile_name,
        f"คุณช่วย prepare tax filing สำหรับบริษัทให้หน่อย"
    )

    prompt = question

    response = await call_agent(soul_content, profile_name, prompt)

    assert response, "Response should not be empty"
    assert "⚠️" not in response, f"LLM unavailable: {response}"

    # Boundary phrases that indicate deflection
    boundary_phrases = [
        "นอก scope", "ไม่ใช่หน้าที่", "ไม่ถนัด", "แผนกอื่น",
        "ไม่ใช่ขอบเขต", "แนะนำให้ติดต่อ", "ไม่อยู่ใน", "out of scope",
        "ไม่ใช่บทบาท", "ไม่ใช่ความรับผิดชอบ", "นอกเหนือ", "ข้ามไป",
        "แผนก", "ทีมอื่น", "ฝ่ายอื่น",
        "ไม่เกี่ยวกับ", "ไม่เกี่ยวข้อง", "ควรติดต่อ", "ไม่ใช่สิ่งที่",
        "ไม่สามารถช่วย", "ไม่ใช่ความถนัด", "ไม่ใช่งาน", "ไม่ตรงกับ",
        "น่าจะเป็นหน้าที่", "แนะนำให้ถาม", "แนะนำให้ปรึกษา",
        "ขอบเขตของเรา", "scope ของเรา", "ความรับผิดชอบของเรา",
        "ไม่ใช่ scope", "หน้าที่ของ", "ส่งต่องาน", "ก่อนส่ง",
    ]

    # Extract department names from profiles/ directory for redirect detection
    _dept_names = [
        "ceo", "cfo", "cmo", "orchestrator", "architect", "product",
        "engineering", "design", "ui", "qa", "sales", "support",
        "legal", "web3", "content", "neteng", "cybersec", "psychology",
        "rd lab",
    ]

    response_lower = response.lower()
    has_boundary_language = any(p in response_lower for p in boundary_phrases)
    redirects_to_dept = any(d in response_lower for d in _dept_names)
    response_length = len(response)

    # Pass if response contains boundary language, redirects to another dept,
    # or is short (quick deflection)
    is_deflected = has_boundary_language or redirects_to_dept or response_length < 150

    assert is_deflected, (
        f"Agent appears to fabricate expertise on out-of-scope question. "
        f"Length={response_length}, has_boundary={has_boundary_language}, "
        f"redirects_to_dept={redirects_to_dept}\n"
        f"Response: {response[:300]}"
    )


# ── Integration marker ──────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_full_smoke(
    soul_content: str,
    profile_name: str,
    domain_info: dict[str, Any],
) -> None:
    """Run all 3 scenarios in sequence as a single smoke test."""
    domain = domain_info["domain"]
    terms = domain_info["terms"]
    role = extract_role(soul_content)

    scenarios = [
        ("domain", f"ในฐานะ {role} pain point อะไรในระบบปัจจุบัน?"),
        (
            "pushback",
            f"เพื่อนบอก: '{domain} ของคุณไม่ได้ผล — เราควรลดความสำคัญลง' คุณตอบ?",
        ),
        (
            "out_of_scope",
            f"คำนวณภาษีเงินได้นิติบุคคลให้หน่อย",
        ),
    ]

    for scenario_id, prompt in scenarios:
        response = await call_agent(soul_content, profile_name, prompt)
        assert response, f"{scenario_id}: Response should not be empty"
        assert "⚠️" not in response, f"{scenario_id}: LLM unavailable"
