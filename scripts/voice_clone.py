#!/usr/bin/env python3
"""voice_clone.py — โคลนเสียงครีเอเตอร์ด้วย OmniVoice (local, ไม่ใช้ API key)

ใช้เมื่อครีเอเตอร์ไม่สะดวกอัดเสียง → ใช้เสียงต้นฉบับที่มีอยู่แล้วเป็นตัวอย่าง (reference)
แล้วให้ระบบอ่านสคริปต์แทน

ตัวอย่างเสียงต้องเป็นภาษาเดียวกับที่จะสังเคราะห์ (แนะนำ 3-10 วิ)

ตัวอย่าง:
  python scripts/voice_clone.py --ref-audio ref16k.wav \\
      --ref-text "แต่ Loop Engineering คือการออกแบบระบบให้ AI รันตัวเองจนสำเร็จครับ" \\
      --text "สวัสดีครับ นี่คือเสียงที่โคลนมา" --out out.wav
"""
from __future__ import annotations

import argparse
import os
import sys
import time
from pathlib import Path

VENV = Path("/data/venvs/omnivoice")
TORCH_LIB = VENV / "lib/python3.12/site-packages/torch/lib"
MODEL = "k2-fsa/OmniVoice"


def main() -> int:
    ap = argparse.ArgumentParser(description="โคลนเสียงด้วย OmniVoice (CPU)")
    ap.add_argument("--ref-audio", required=True, help="เสียงตัวอย่าง 3-10 วิ (16kHz mono)")
    ap.add_argument("--ref-text", default="", help="ข้อความของเสียงตัวอย่าง (เว้นว่าง = ให้ ASR ถอดเอง)")
    ap.add_argument("--text", required=True, help="ข้อความที่จะสังเคราะห์")
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default=MODEL)
    args = ap.parse_args()

    os.environ["LD_LIBRARY_PATH"] = f"{TORCH_LIB}:{os.environ.get('LD_LIBRARY_PATH','')}"
    sys.path.insert(0, str(VENV / "lib/python3.12/site-packages"))

    import numpy as np
    import soundfile as sf
    import torch
    from omnivoice import OmniVoice

    ref = Path(args.ref_audio)
    if not ref.exists():
        print(f"❌ ไม่พบไฟล์เสียงอ้างอิง: {ref}")
        return 1
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    print(f"⏳ โหลดโมเดล {args.model} (CPU, ~2.5GB) …", flush=True)
    model = OmniVoice.from_pretrained(
        args.model,
        device_map="cpu",
        dtype=torch.float32,
    )
    print(f"   ✅ โหลดเสร็จ {time.time()-t0:.0f} วิ", flush=True)

    t1 = time.time()
    print(f"🎤 สังเคราะห์: {args.text[:60]}", flush=True)
    audio = model.generate(
        text=args.text,
        ref_audio=str(ref),
        ref_text=(args.ref_text or None),
    )
    dt = time.time() - t1

    arr = np.concatenate(audio) if isinstance(audio, list) else np.asarray(audio)
    sr = 24000
    sf.write(str(out), arr, sr)
    dur = len(arr) / sr
    print(f"✅ เสร็จ: {out}")
    print(f"   {dur:.1f} วิ เสียเวลา {dt:.0f} วิ (RTF {dt/max(dur,0.01):.2f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
