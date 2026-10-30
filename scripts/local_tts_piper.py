#!/usr/bin/env python3
"""Run an already-installed Piper model without network access."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT_DIR = Path(os.environ.get("SOLOCORP_BUS_ROOT", ROOT / "central_bus")) / "content"
DEFAULT_MODEL = ROOT / "tools" / "piper" / "models" / "th_TH-tsync2-medium.onnx"
DEFAULT_CONFIG = Path(f"{DEFAULT_MODEL}.json")
MAX_TEXT_CHARS = 20_000


def _local_path(path: Path, label: str, *, must_exist: bool) -> Path:
    resolved = path.expanduser().resolve(strict=must_exist)
    root = CONTENT_DIR.resolve()
    if label == "output" and not resolved.is_relative_to(root):
        raise ValueError("output must resolve inside central_bus/content")
    if must_exist and not resolved.is_file():
        raise ValueError(f"{label} must be a regular file")
    return resolved


def _piper_binary() -> str:
    configured = os.environ.get("PIPER_BIN", "").strip()
    candidates = [configured, "/data/venvs/tts/bin/piper", shutil.which("piper") or ""]
    for candidate in candidates:
        if candidate and Path(candidate).is_file() and os.access(candidate, os.X_OK):
            return candidate
    raise FileNotFoundError("local Piper executable not found; set PIPER_BIN")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--text-file", type=Path)
    parser.add_argument("--model", type=Path, default=DEFAULT_MODEL)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--license", default="unknown", help="self-reported model license")
    args = parser.parse_args()

    try:
        if args.text_file:
            text_path = _local_path(args.text_file, "text file", must_exist=True)
            text = text_path.read_text(encoding="utf-8")
        else:
            text = sys.stdin.read()
        text = text.strip()
        if not text or len(text) > MAX_TEXT_CHARS:
            raise ValueError(f"text must contain 1-{MAX_TEXT_CHARS} characters")

        model = _local_path(args.model, "model", must_exist=True)
        config = _local_path(args.config, "config", must_exist=True)
        output = _local_path(args.output, "output", must_exist=False)
        if output.suffix.lower() != ".wav":
            raise ValueError("output must use the .wav extension")
        if output.exists() or output.is_symlink():
            raise FileExistsError(f"refusing to overwrite output: {output}")
        output.parent.mkdir(parents=True, exist_ok=True)

        command = [_piper_binary(), "--model", str(model), "--config", str(config), "--output_file", str(output)]
        result = subprocess.run(
            command,
            input=text + "\n",
            text=True,
            capture_output=True,
            timeout=300,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Piper failed with exit code {result.returncode}: {result.stderr[-1000:]}")
        if not output.is_file() or output.stat().st_size <= 44:
            raise RuntimeError("Piper did not produce a valid WAV file")
        with wave.open(str(output), "rb") as wav:
            audio = {
                "sample_rate": wav.getframerate(),
                "channels": wav.getnchannels(),
                "frames": wav.getnframes(),
                "duration_seconds": round(wav.getnframes() / wav.getframerate(), 3),
            }
        report = {
            "status": "completed",
            "engine": "piper-local",
            "model": model.name,
            "model_sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            "model_license": args.license,
            "model_rights_status": "human_confirmation_required",
            "output": str(output),
            "bytes": output.stat().st_size,
            "audio": audio,
            "network_used": False,
        }
        print(json.dumps(report, ensure_ascii=False))
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
        print(json.dumps({"status": "failed", "error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
