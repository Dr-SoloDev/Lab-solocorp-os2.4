#!/usr/bin/env bash
# setup_tts.sh — ติดตั้งสายเสียงพูดไทย (local, ไม่ใช้ API key)
#
# ผลลัพธ์: เสียงไทย th_TH-tsync2-medium (piper + tltk) ที่ /data/models/piper
# ใช้โดย scripts/make_clip.py
set -euo pipefail

VENV="${TTS_VENV:-/data/venvs/tts}"
MODEL_DIR="${PIPER_MODEL_DIR:-/data/models/piper}"
VOICE="th_TH-tsync2-medium"
BASE="https://huggingface.co/rhasspy/piper-voices/resolve/main/th/th_TH/tsync2/medium/${VOICE}"

echo "=== 1) venv ==="
if [[ ! -x "$VENV/bin/python" ]]; then
  python3 -m venv "$VENV"
fi
"$VENV/bin/python" -m pip install -q --upgrade pip

echo "=== 2) piper + tltk (ต้อง --no-deps เพราะ tltk จะ build scikit-learn เก่า) ==="
"$VENV/bin/pip" install -q --only-binary :all: numpy scipy scikit-learn joblib threadpoolctl
"$VENV/bin/pip" install -q piper-tts
"$VENV/bin/pip" install -q --no-deps tltk
"$VENV/bin/pip" install -q pandas nltk requests beautifulsoup4 tqdm gensim sklearn-crfsuite unicode-rbnf

echo "=== 3) โมเดลเสียงไทย (63MB) ==="
mkdir -p "$MODEL_DIR"
[[ -f "$MODEL_DIR/${VOICE}.onnx" ]] || curl -sL -o "$MODEL_DIR/${VOICE}.onnx" "$BASE.onnx"
[[ -f "$MODEL_DIR/${VOICE}.onnx.json" ]] || curl -sL -o "$MODEL_DIR/${VOICE}.onnx.json" "$BASE.onnx.json"

echo "=== 4) ทดสอบ ==="
"$VENV/bin/python" - <<PY
import wave, numpy as np
from piper import PiperVoice
v = PiperVoice.load("$MODEL_DIR/${VOICE}.onnx", config_path="$MODEL_DIR/${VOICE}.onnx.json")
chunks = list(v.synthesize("ทดสอบเสียงพูดภาษาไทย"))
arr = np.concatenate([c.audio_float_array for c in chunks])
sr = chunks[0].sample_rate
with wave.open("/tmp/_tts_test.wav","wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(arr,-1,1)*32767).astype(np.int16).tobytes())
print(f"✅ เสียงไทยใช้ได้ — {len(arr)/sr:.1f}s @ {sr}Hz")
PY
rm -f /tmp/_tts_test.wav
echo "🎉 เสร็จ — ใช้ scripts/make_clip.py ได้เลย"
