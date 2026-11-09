#!/usr/bin/env python3
"""Poll every department head agent for opinion on SoloCorp OS -> AXIS transformation.

Usage: python scripts/axis_opinion_poll.py [--only cfo,qa] [--out-dir DIR]
Each agent gets 1 think() call (short). Stops gracefully on quota lock.
"""

from __future__ import annotations

import argparse
import asyncio
import importlib
import json
import sys
from datetime import date, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from workers.agents.base_agent import BaseAgent  # noqa: E402

MODULES = [
    "architect_agent",
    "cfo_agent",
    "cmo_agent",
    "content_agent",
    "coo_dispatch_agent",
    "cybersec_agent",
    "design_agent",
    "engineering_agent",
    "legal_agent",
    "neteng_agent",
    "orchestrator_agent",
    "product_agent",
    "psychology_agent",
    "qa_agent",
    "rd_lab_agent",
    "sales_agent",
    "support_agent",
    "ui_agent",
    "web3_agent",
]

PROMPT = (
    "องค์กร SoloCorp OS กำลังรีแบรนด์เป็น AXIS Framework "
    "(One Axis, Multiple Identities): package code solocorp_mcp->axis_mcp, "
    "skills @solocorp->@axis, เพิ่ม agent CEO ใหม่ axis-ceo, MCP 10 ตัวเขียวครบ, "
    "pytest 1187 ผ่าน. ในฐานะ {role} ให้ความเห็นสั้นๆ 3 บรรทัดเท่านั้น: "
    "1) ประโยชน์ต่อแผนกคุณ 2) ความเสี่ยง/ห่วง 1 ข้อ 3) คะแนนสนับสนุน 1-10"
)


def load_heads() -> list[BaseAgent]:
    heads = []
    for mod in MODULES:
        m = importlib.import_module(f"workers.agents.{mod}")
        for name in dir(m):
            obj = getattr(m, name)
            if (
                isinstance(obj, type)
                and issubclass(obj, BaseAgent)
                and obj is not BaseAgent
                and "Mock" not in name
            ):
                try:
                    heads.append(obj())
                    break
                except Exception as e:  # noqa: BLE001
                    print(f"skip {mod}.{name}: {e}")
    return heads


async def poll_one(agent: BaseAgent) -> dict:
    t0 = datetime.now()
    try:
        text = await agent.think(PROMPT.format(role=agent.name), max_tokens=400)
    except Exception as exc:  # noqa: BLE001
        text = f"ERROR: {type(exc).__name__}: {exc}"
    locked = text.startswith("⚠️ LLM ไม่พร้อม")
    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "seconds": round((datetime.now() - t0).total_seconds(), 1),
        "quota_locked": locked,
        "opinion": text[:1200],
    }


async def main_async(args) -> int:
    only = (
        {s.strip() for s in args.only.split(",") if s.strip()} if args.only else set()
    )
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    heads = [
        h
        for h in load_heads()
        if not only or h.agent_id in only or h.agent_id.split("-")[0] in only
    ]
    print(f"heads: {len(heads)}", flush=True)
    rows = []
    for h in heads:
        print(f"- {h.agent_id} ...", flush=True)
        r = await poll_one(h)
        rows.append(r)
        (out / "opinions.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        print(
            f"  -> {r['seconds']}s {'LOCKED-STOP' if r['quota_locked'] else 'ok'}",
            flush=True,
        )
        if r["quota_locked"]:
            print("quota locked — stopping, rest marked pending", flush=True)
            break
    done = {r["agent_id"] for r in rows if not r["quota_locked"]}
    md = [
        "# AXIS Transformation — ความเห็นหัวหน้าแผนก",
        "",
        f"- วันที่: {datetime.now().isoformat(timespec='seconds')}",
        f"- ตอบแล้ว: {len(done)}/{len(MODULES)}",
        "",
        "| แผนก | เวลา | ความเห็น |",
        "|:--|--:|:--|",
    ]
    for r in rows:
        md.append(
            f"| {r['agent_id']} | {r['seconds']}s | {r['opinion'].replace(chr(10), '<br>').replace('|', '/')} |"
        )
    (out / "table.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"saved: {out}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    ap.add_argument(
        "--out-dir",
        default=str(
            REPO / "bus" / "evidence" / date.today().isoformat() / "axis-opinions"
        ),
    )
    return asyncio.run(main_async(ap.parse_args()))


if __name__ == "__main__":
    raise SystemExit(main())
