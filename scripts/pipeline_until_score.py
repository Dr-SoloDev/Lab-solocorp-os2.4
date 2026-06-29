#!/usr/bin/env python3
"""Run pipeline executor until bangkok-pos scores >= 7/10."""
import subprocess, json, sys, time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from central_bus import queue, state
from central_bus.models import BusMessage

PROJECT_ID = "bangkok-pos"
PROJECT_PATH = "/home/drsolodev/projects/bangkok-pos"
TARGET_SCORE = 7
MAX_ROUNDS = 10

SCORE_PROMPT = """คุณคือ QA ทีม ของ SoloCorp — ประเมินคะแนนโปรเจกต์ bangkok-pos

ตรวจสอบจริงใน /home/drsolodev/projects/bangkok-pos:
1. DB + seed data พร้อมไหม (0-2)
2. Bottom nav + routing ครบไหม (0-2)
3. จำนวน pages ที่ใช้งานได้จริง: dashboard/purchase-orders/sale-lots/catalog/inventory/sellers/expenses/branches (0-3)
4. Mobile responsive 375px ไหม (0-1)
5. ไม่มี TypeScript error ร้ายแรงไหม (0-2)

รวมคะแนน /10 แล้วตอบในรูปแบบ JSON เท่านั้น:
{"score": <number>, "breakdown": {"db_seed": <0-2>, "nav": <0-2>, "pages": <0-3>, "responsive": <0-1>, "ts_errors": <0-2>}, "missing": ["<สิ่งที่ยังขาด>", ...]}"""

GAP_TASKS = {
    "nav":    ("s-nav",  "engineering", "high",   "Fix bottom nav: สร้าง BottomNav component ใน src/components/BottomNav.tsx แล้วใส่ใน dashboard/layout.tsx — links: /dashboard /dashboard/purchase-orders /dashboard/sale-lots /dashboard/catalog /dashboard/inventory /dashboard/sellers /dashboard/expenses /dashboard/branches"),
    "db_seed":("s-seed", "engineering", "high",   "รัน npx prisma db seed ใน /home/drsolodev/projects/bangkok-pos"),
    "po":     ("s-po",   "engineering", "normal",  "สร้าง src/app/dashboard/purchase-orders/page.tsx — list + create modal ใช้ api.purchaseOrder"),
    "sale":   ("s-sl",   "engineering", "normal",  "สร้าง src/app/dashboard/sale-lots/page.tsx — list + create modal ใช้ api.saleLot"),
    "cat":    ("s-cat",  "engineering", "normal",  "สร้าง src/app/dashboard/catalog/page.tsx — CRUD ใช้ api.catalog"),
    "inv":    ("s-inv",  "engineering", "normal",  "สร้าง src/app/dashboard/inventory/page.tsx — stock list ใช้ api.product"),
    "sel":    ("s-sel",  "engineering", "normal",  "สร้าง src/app/dashboard/sellers/page.tsx — CRUD ใช้ api.seller"),
    "exp":    ("s-exp",  "engineering", "normal",  "สร้าง src/app/dashboard/expenses/page.tsx — CRUD ใช้ api.expense"),
    "bra":    ("s-bra",  "engineering", "normal",  "สร้าง src/app/dashboard/branches/page.tsx — CRUD ใช้ api.branch"),
}

def queue_depth() -> int:
    total = 0
    for p in ("high", "normal"):
        f = Path(f"bus/queue/{p}.jsonl")
        if f.exists() and f.stat().st_size > 0:
            total += len([l for l in f.read_text().splitlines() if l.strip()])
    return total

def drain_and_execute():
    """Run executor until queue empty."""
    from loop_runner.loops.pipeline_executor import PipelineExecutorLoop
    loop = PipelineExecutorLoop()
    loop.interval = __import__("datetime").timedelta(seconds=0)  # bypass interval
    while queue_depth() > 0:
        result = loop.run()
        print(result)
        remaining = queue_depth()
        print(f"  📬 remaining: {remaining}")
        if remaining == 0:
            break

def score_project() -> dict:
    r = subprocess.run(
        ["claude", "--dangerously-skip-permissions", "-p", SCORE_PROMPT],
        capture_output=True, text=True, timeout=120, cwd=PROJECT_PATH,
    )
    output = r.stdout.strip()
    # Extract JSON from output
    start = output.find("{")
    end = output.rfind("}") + 1
    if start >= 0 and end > start:
        try:
            return json.loads(output[start:end])
        except Exception:
            pass
    return {"score": 0, "breakdown": {}, "missing": ["parse error"]}

def enqueue_gaps(missing: list[str]):
    """Enqueue tasks for identified gaps."""
    keywords = {
        "nav": ["nav", "bottom", "routing"],
        "db_seed": ["seed", "db", "data"],
        "po": ["purchase", "order"],
        "sale": ["sale", "lot"],
        "cat": ["catalog"],
        "inv": ["inventory", "stock"],
        "sel": ["seller"],
        "exp": ["expense"],
        "bra": ["branch"],
    }
    enqueued = []
    for gap_key, keywords_list in keywords.items():
        if any(kw in " ".join(missing).lower() for kw in keywords_list):
            task_id, dept, prio, desc = GAP_TASKS[gap_key]
            queue.enqueue(BusMessage(
                from_dept="architect", to_dept=dept, type="task",
                project_id=PROJECT_ID, phase="dev",
                payload={"task_id": task_id, "description": desc},
                trace_id=f"bkk-gap-{task_id}", priority=prio,
            ))
            enqueued.append(task_id)
    return enqueued


if __name__ == "__main__":
    for round_num in range(1, MAX_ROUNDS + 1):
        print(f"\n{'='*50}")
        print(f"🔄 Round {round_num}/{MAX_ROUNDS}")
        print(f"{'='*50}")

        drain_and_execute()

        print("\n🔍 Scoring project...")
        result = score_project()
        score = result.get("score", 0)
        breakdown = result.get("breakdown", {})
        missing = result.get("missing", [])

        print(f"\n📊 Score: {score}/10")
        for k, v in breakdown.items():
            print(f"   {k}: {v}")
        if missing:
            print(f"   missing: {missing}")

        if score >= TARGET_SCORE:
            print(f"\n✅ เป้าหมายสำเร็จ! score={score}/10 >= {TARGET_SCORE}")
            state.update_phase(PROJECT_ID, "dev", "done", owner="engineering")
            state.update_phase(PROJECT_ID, "qa", "in_progress", owner="qa")
            break

        if round_num == MAX_ROUNDS:
            print(f"\n⚠️ ครบ {MAX_ROUNDS} rounds แล้ว score={score}/10 — หยุด")
            break

        enqueued = enqueue_gaps(missing)
        if not enqueued:
            print("⚠️ ไม่มี gap task เพิ่มเติม — หยุด loop")
            break
        print(f"\n➕ Re-enqueued {len(enqueued)} gap tasks: {enqueued}")
        time.sleep(2)
