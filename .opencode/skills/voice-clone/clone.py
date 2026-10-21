"""
โคลนเสียง + สร้างเสียงพากย์ ด้วย OmniVoice (zero-shot voice cloning)

ใช้เมื่อมนุษย์สั่ง "ทำวิดีโอด้วยเสียงนี้" / "พากย์เสียงให้หน่อย" / "โคลนเสียง"

ตัวอย่าง:
    python clone.py "ข้อความที่อยากให้พูด"
    python clone.py "ข้อความ" --out clip01.wav
    python clone.py "ข้อความ" --steps 32
    python clone.py --setup "C:/path/to/video.mp4"
"""
import argparse
import os
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = os.path.expanduser("~")
ASSET_DIR = os.environ.get("OMNIVOICE_ASSETS") or os.path.join(HOME, "Desktop", "OmniVoice")
VENV = os.environ.get("OMNIVOICE_VENV") or os.path.join(
    os.environ.get("LOCALAPPDATA", os.path.join(HOME, "AppData", "Local")),
    "Temp", "opencode", "omnivoice-venv",
)
REF = os.path.join(ASSET_DIR, "voice.wav")
PROMPT = os.path.join(ASSET_DIR, "voice_prompt.pt")


def die(msg, code=1):
    print("ERROR: " + msg)
    sys.exit(code)


def setup(source):
    """แปลงไฟล์ต้นทาง (mp4/mp3/m4a/...) เป็น voice.wav mono 24kHz + ตรวจความยาว"""
    os.makedirs(ASSET_DIR, exist_ok=True)
    ffmpeg = shutil_which("ffmpeg")
    if not ffmpeg:
        die("ไม่พบ ffmpeg — ติดตั้งก่อน (winget install Gyan.FFmpeg)")
    cmd = [ffmpeg, "-y", "-i", source, "-vn", "-ac", "1", "-ar", "24000",
           "-c:a", "pcm_s16le", REF]
    print("กำลังแปลง: " + source)
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        die("ffmpeg ล้มเหลว:\n" + r.stderr.decode("utf-8", "replace")[-800:])
    import wave
    with wave.open(REF) as w:
        dur = w.getnframes() / w.getframerate()
    print("ได้ voice.wav = %.2f วินาที" % dur)
    if not (3.0 <= dur <= 12.0):
        print("WARN: ความยาวอยู่นอกช่วง 3-12 วิ — คุณภาพอาจตก")
    if os.path.exists(PROMPT):
        os.remove(PROMPT)
        print("ลบ prompt เดิม (เสียงต้นแบบเปลี่ยน)")


def shutil_which(name):
    from shutil import which
    return which(name)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("text", nargs="?", help="ข้อความที่ให้เสียงพูด")
    ap.add_argument("--setup", help="แปลงไฟล์เสียง/วิดีโอเป็นเสียงต้นแบบ")
    ap.add_argument("--out", help="ชื่อไฟล์ผลลัพธ์ (ค่าเริ่มต้น clone_result.wav)")
    ap.add_argument("--steps", type=int, default=16, help="diffusion steps (16 เร็ว / 32 คุณภาพ)")
    ap.add_argument("--speed", type=float, default=1.0, help="<1 ช้าลง, >1 เร็วขึ้น")
    args = ap.parse_args()

    if args.setup:
        if not os.path.exists(args.setup):
            die("ไม่พบไฟล์: " + args.setup)
        return setup(args.setup)

    if not args.text:
        die("ต้องใส่ข้อความ หรือใช้ --setup <ไฟล์> เพื่อเตรียมเสียงต้นแบบ")

    if not os.path.exists(REF):
        die("ไม่พบเสียงต้นแบบ %s\n"
            "สั่ง:  python clone.py --setup <ไฟล์ mp4/mp3 ของมนุษย์>\n"
            "ต้องเป็นเสียงพูดล้วน 3-12 วินาที ห้องเงียบ ไม่มีเพลง" % REF)

    import soundfile as sf
    import torch
    from omnivoice import OmniVoice

    print("กำลังโหลดโมเดล... (ครั้งแรก ~60 วินาที)")
    model = OmniVoice.from_pretrained("k2-fsa/OmniVoice", device_map="cuda:0", dtype=torch.float16)

    out = args.out or os.path.join(ASSET_DIR, "clone_result.wav")
    if not os.path.isabs(out):
        out = os.path.join(ASSET_DIR, out)

    print("กำลังสร้างเสียง...")
    t = time.time()

    if os.path.exists(PROMPT):
        from omnivoice import VoiceClonePrompt
        prompt = VoiceClonePrompt.load(PROMPT)
        print("ใช้ prompt ที่บันทึกไว้")
    else:
        prompt = model.create_voice_clone_prompt(ref_audio=REF)
        prompt.save(PROMPT)
        print("บันทึก prompt ใหม่แล้ว")

    audio = model.generate(text=args.text, voice_clone_prompt=prompt,
                           num_step=args.steps, speed=args.speed)

    sec = time.time() - t
    dur = len(audio[0]) / 24000
    sf.write(out, audio[0], 24000)

    print("-" * 44)
    print("ข้อความ  : " + args.text)
    print("ใช้เวลา : %.2f วินาที" % sec)
    print("ความยาว : %.2f วินาที  (RTF %.2f)" % (dur, sec / dur))
    print("ผลลัพธ์ : " + out)
    print("CLONE_OK")


if __name__ == "__main__":
    main()
