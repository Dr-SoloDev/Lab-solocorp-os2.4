#!/usr/bin/env python
"""
content_render.py — SoloCorp คนงานคนแรก (content-creator, D2)

รับสเปก .json = เรื่องที่จะทำ  ->  สั่ง Concat MCP  ->  ได้ .mp4
ไม่คิดเนื้อหาเอง · ไม่แตะอะไรนอก location ที่สเปกระบุ · รายงานผลเป็น JSON + exit code

ใช้:  python scripts/content_render.py spec.json
"""
import json
import os
import shutil
import subprocess
import sys
import time


def _find_concat() -> str:
    """หา binary ของ Concat MCP — ไม่ hardcode path ของเครื่องใคร

    ลำดับ: CONCAT_BIN env → PATH → ตำแหน่งที่พบบ่อย (macOS/Linux/Windows)
    ถ้าหาไม่เจอ → บอกชัดว่าต้องตั้ง env ไม่ใช่ crash เงียบ ๆ
    """
    env = os.environ.get("CONCAT_BIN")
    if env:
        return env

    found = shutil.which("concat")
    if found:
        return found

    for candidate in (
        "/Applications/Concat.app/Contents/MacOS/concat",
        "/usr/local/bin/concat",
        "/opt/concat/concat",
        os.path.expandvars(r"%LOCALAPPDATA%\Programs\Concat\concat.exe"),
    ):
        if candidate and os.path.isfile(candidate):
            return candidate

    raise SystemExit(
        "❌ หา Concat MCP binary ไม่เจอ\n"
        "   ตั้ง env ก่อนแล้วรัน:\n"
        "     export CONCAT_BIN=/path/to/concat\n"
        "   (Windows: set CONCAT_BIN=C:\\path\\to\\concat.exe)"
    )


CONCAT = _find_concat()


class Concat:
    """client JSON-RPC ไปที่ Concat MCP (stdio)"""

    def __init__(self):
        self.p = subprocess.Popen(
            [CONCAT, "--mcp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, text=True, encoding="utf-8", bufsize=1)
        self.n = 0
        self.call("concat_version")

    def call(self, name, args=None):
        self.n += 1
        req = {"jsonrpc": "2.0", "id": self.n, "method": "tools/call",
               "params": {"name": name, "arguments": args or {}}}
        self.p.stdin.write(json.dumps(req, ensure_ascii=False) + "\n")
        self.p.stdin.flush()
        while True:
            line = self.p.stdout.readline()
            if not line:
                raise RuntimeError("concat mcp ปิดตัวไปก่อนจะตอบ")
            m = json.loads(line)
            if m.get("id") != self.n:
                continue
            if "error" in m:
                raise RuntimeError(f"{name}: {m['error'].get('message')}")
            txt = "".join(c.get("text", "") for c in m["result"].get("content", []))
            if m["result"].get("isError") or not txt.lstrip().startswith(("{", "[")):
                # Concat ส่ง error กลับมาเป็นข้อความธรรมดา ไม่ได้ตั้ง isError เสมอ
                raise RuntimeError(f"{name}: {txt.strip()[:200]}")
            return txt

    def obj(self, name, args=None):
        return json.loads(self.call(name, args))

    def close(self):
        try:
            self.p.stdin.close()
            self.p.wait(timeout=15)
        except Exception:
            self.p.kill()


def fwd(p):
    """Windows ต้องใช้ / ใน path ของ Concat"""
    return p.replace("\\", "/")


def render(spec):
    out = {"steps": [], "clip_count": 0}
    loc = fwd(spec["location"])
    c = Concat()

    print(f"[1/6] project_create -> {spec['project']}", flush=True)
    v = spec.get("video", {})
    c.call("project_create", {
        "name": spec["project"], "location": loc,
        "video": {"width": v.get("width", 1080), "height": v.get("height", 1920),
                  "rateNum": v.get("fps", 30), "rateDen": 1}})
    out["steps"].append("project_create")

    if spec.get("background"):
        c.call("timeline_background", {
            "path": f"{loc}/{spec['project']}", "timelineId": "TL1",
            "background": spec["background"]})
        out["steps"].append("background")

    if spec.get("font"):
        c.call("edit_apply", {"path": f"{loc}/{spec['project']}",
                              "command": {"op": "addFont",
                                          "family": spec["font"]["family"],
                                          "path": spec["font"]["path"]}})
        out["steps"].append("font")

    for card in spec.get("cards", []):
        st = {"fontFamily": f'"{spec["font"]["family"]}"' if spec.get("font") else None,
              "fontSize": card.get("size", 0.046), "fontWeight": card.get("weight", 600),
              "color": card.get("color", "#F5EDE0"), "align": "center",
              "lineHeight": 1.65, "maxWidth": card.get("width", 0.84),
              "background": card.get("plate", ""), "content": card["text"]}
        st = {k: v2 for k, v2 in st.items() if v2 is not None}
        if card.get("plate"):
            st["backgroundPaddingX"] = 0.06
            st["backgroundPaddingY"] = 0.03
        c.call("title_add", {"path": f"{loc}/{spec['project']}", "start": card["start"],
                             "duration": round(card["end"] - card["start"], 3),
                             "style": st, "trackId": spec.get("text_track", "T2")})
        out["clip_count"] += 1
    out["steps"].append(f"cards={out['clip_count']}")

    bin_ids = {}
    proj = f"{loc}/{spec['project']}"
    for snd in spec.get("sounds", []):
        f = fwd(snd["file"])
        if f not in bin_ids:
            res = c.obj("media_import", {"path": proj, "file": f})
            mid = res.get("createdId")
            if not mid:            # import ซ้ำ = no-op ต้องหา id เดิมจาก bin
                mid = next((m["id"] for m in res.get("media", [])
                            if m["path"].lower() == f.lower()), None)
            if not mid:
                raise RuntimeError(f"media_import ไม่คืน mediaId: {f}")
            bin_ids[f] = mid
        c.call("clip_add", {"path": proj, "mediaId": bin_ids[f],
                            "start": snd["start"], "trackId": snd.get("track", "T1")})
        if snd.get("volume"):
            clip = c.obj("timeline_read", {"path": proj})["timeline"]["clips"]
            cid = [x["id"] for x in clip if x["name"] == os.path.basename(snd["file"])]
            if cid:
                c.call("clip_update", {"path": proj, "clipId": cid[-1],
                                       "patch": {"volume": snd["volume"]}})
    out["steps"].append(f"sounds={len(spec.get('sounds', []))}")

    c.call("project_save", {"path": proj})
    job = c.obj("export_start", {"path": proj, "output": fwd(spec["output"]),
                                 "crf": spec.get("crf", 20)})["job"]
    res = json.loads(c.call("export_wait", {"job": job, "timeoutSeconds": 900}))
    c.call("project_close", {"path": proj})
    c.close()

    if res.get("state") != "done":
        raise RuntimeError(f"export ไม่สำเร็จ: {res}")
    out["export"] = {"state": res["state"], "frames": res.get("total"),
                     "width": res.get("width"), "height": res.get("height"),
                     "output": spec["output"],
                     "bytes": os.path.getsize(spec["output"]) if os.path.exists(spec["output"]) else 0}
    return out


def main():
    if len(sys.argv) < 2:
        print("ใช้: python content_render.py <spec.json>", file=sys.stderr)
        return 2
    t0 = time.time()
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    try:
        out = render(spec)
        out["seconds"] = round(time.time() - t0, 1)
        print(json.dumps(out, ensure_ascii=False, indent=2))
        print("CONTENT_RENDER_OK")
        return 0
    except Exception as e:
        print(f"CONTENT_RENDER_FAIL: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())