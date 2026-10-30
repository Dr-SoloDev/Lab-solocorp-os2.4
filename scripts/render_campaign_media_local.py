#!/usr/bin/env python3
"""Render timed synthetic campaign scenes using only local engines."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import subprocess
import sys
import textwrap
import wave
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BUS_ROOT = Path(os.environ.get("SOLOCORP_BUS_ROOT", ROOT / "central_bus")).resolve()
CONTENT_DIR = BUS_ROOT / "content"
PIPER_SCRIPT = ROOT / "scripts" / "local_tts_piper.py"
SCENE_SCRIPT = ROOT / "scripts" / "render_pdoom_scenes.mjs"
FFMPEG = os.environ.get("FFMPEG_BIN") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE_BIN") or "ffprobe"
FPS = 30


def _run(command: list[str], *, input_text: str | None = None, timeout: int = 900) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        input=input_text,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
        cwd=ROOT,
    )


def _must_succeed(result: subprocess.CompletedProcess[str], label: str) -> None:
    if result.returncode != 0:
        raise RuntimeError(f"{label} failed ({result.returncode}): {result.stderr[-1600:]}")


def _ass_time(seconds: int) -> str:
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours}:{minutes:02d}:{seconds:02d}.00"


def _escape_ass(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _write_subtitles(scenes: list[dict[str, Any]], path: Path) -> None:
    lines = [
        "[Script Info]", "ScriptType: v4.00+", "PlayResX: 1080", "PlayResY: 1920", "WrapStyle: 2", "",
        "[V4+ Styles]", "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
        "Style: Default,Noto Sans Thai,42,&H00FFFFFF,&H0000FFFF,&H00101B26,&H9909151E,0,0,0,0,100,100,0,0,1,2.5,0.8,2,72,72,260,1", "",
        "[Events]", "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    for i, scene in enumerate(scenes):
        caption = "\\N".join(
            _escape_ass(line)
            for line in textwrap.wrap(scene["voiceover"], width=34, break_long_words=True, break_on_hyphens=False)
        )
        lines.append(
            f"Dialogue: 0,{_ass_time(scene['start_seconds'])},{_ass_time(scene['end_seconds'])},Default,,0,0,0,,{caption}"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _filter_path(path: Path) -> str:
    value = str(path.resolve())
    return value.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _measure_ebur128(path: Path) -> dict[str, float]:
    result = _run([
        FFMPEG, "-hide_banner", "-loglevel", "info", "-i", str(path), "-map", "0:a:0",
        "-af", "ebur128=peak=true:framelog=quiet", "-f", "null", "-",
    ], timeout=900)
    _must_succeed(result, "EBU R128 loudness measurement")
    integrated = re.search(
        r"Integrated loudness:\s+I:\s+([-+0-9.]+)\s+LUFS", result.stderr
    )
    true_peak = re.search(r"True peak:\s+Peak:\s+([-+0-9.]+)\s+dBFS", result.stderr)
    if not integrated or not true_peak:
        raise RuntimeError("FFmpeg did not return complete EBU R128 measurements")
    return {
        "integrated_lufs": float(integrated.group(1)),
        "true_peak_dbtp": float(true_peak.group(1)),
    }


def render(payload: dict[str, Any]) -> dict[str, Any]:
    campaign_id = str(payload.get("campaign_id", "")).strip()
    scenes = payload.get("scenes")
    output_dir = Path(str(payload.get("output_dir", ""))).expanduser().resolve()
    model_license = str(payload.get("model_license", "unknown"))
    scene_seconds = payload.get("scene_seconds", 15)
    if isinstance(scene_seconds, bool) or not isinstance(scene_seconds, int):
        raise ValueError("scene_seconds must be an integer")
    if not campaign_id or not isinstance(scenes, list):
        raise ValueError("campaign_id and a scene list are required")
    if (len(scenes), scene_seconds) not in {(6, 15), (10, 10)}:
        raise ValueError("renderer supports six 15-second scenes or ten 10-second episodes")
    duration_seconds = payload.get("duration_seconds", len(scenes) * scene_seconds)
    if isinstance(duration_seconds, bool) or not isinstance(duration_seconds, int):
        raise ValueError("duration_seconds must be an integer")
    if duration_seconds != len(scenes) * scene_seconds:
        raise ValueError("duration_seconds must equal scene_count × scene_seconds")
    if not output_dir.is_relative_to(CONTENT_DIR.resolve()):
        raise ValueError("output_dir must be inside central_bus/content")
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError(f"refusing to overwrite render directory: {output_dir}")
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict) or not all(isinstance(scene.get(key), str) and scene[key].strip() for key in ("title", "description", "voiceover")):
            raise ValueError(f"scene {index + 1} requires title, description, and voiceover text")
        if scene.get("start_seconds") != index * scene_seconds or scene.get("end_seconds") != (index + 1) * scene_seconds:
            raise ValueError(f"scene {index + 1} must use contiguous {scene_seconds}-second timing")
        if len(scene["voiceover"]) > 5000:
            raise ValueError(f"scene {index + 1} voiceover exceeds the local TTS limit")

    output_dir.mkdir(parents=True, exist_ok=False)
    image_dir = output_dir / "frames"
    image_dir.mkdir()
    voice_dir = output_dir / "voice"
    voice_dir.mkdir()
    model = ROOT / "tools" / "piper" / "models" / "th_TH-tsync2-medium.onnx"
    config = Path(f"{model}.json")
    if not model.is_file() or not config.is_file():
        raise FileNotFoundError("local Thai Piper model/config not installed under tools/piper/models")

    voices: list[Path] = []
    voice_reports: list[dict[str, Any]] = []
    for index, scene in enumerate(scenes):
        voice = voice_dir / f"scene-{index + 1:02d}.wav"
        result = _run(
            [sys.executable, str(PIPER_SCRIPT), "--output", str(voice), "--model", str(model), "--config", str(config), "--license", model_license],
            input_text=scene["voiceover"],
            timeout=360,
        )
        _must_succeed(result, f"Piper scene {index + 1}")
        voice_reports.append(json.loads(result.stdout))
        with wave.open(str(voice), "rb") as wav:
            voice_duration = wav.getnframes() / wav.getframerate()
        if voice_duration > scene_seconds:
            raise RuntimeError(
                f"scene {index + 1} voiceover is {voice_duration:.2f}s and exceeds its {scene_seconds}-second slot"
            )
        voices.append(voice)

    scene_result = _run(["node", str(SCENE_SCRIPT), str(image_dir)], input_text=json.dumps(scenes, ensure_ascii=False), timeout=600)
    _must_succeed(scene_result, "Three.js scene renderer")
    frame_report = json.loads(scene_result.stdout)
    frames = [Path(item).resolve() for item in frame_report["frames"]]
    if len(frames) != len(scenes) or any(not frame.is_file() for frame in frames):
        raise RuntimeError(f"scene renderer did not produce {len(scenes)} frame assets")

    padded_voices: list[Path] = []
    for index, voice in enumerate(voices):
        padded = voice_dir / f"scene-{index + 1:02d}-padded.wav"
        result = _run([
            FFMPEG, "-hide_banner", "-loglevel", "error", "-n", "-i", str(voice),
            "-af", f"silenceremove=start_periods=1:start_duration=0.4:start_threshold=-35dB:stop_periods=-1:stop_duration=0.4:stop_threshold=-35dB,apad=pad_dur={scene_seconds},atrim=duration={scene_seconds}",
            "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(padded),
        ])
        _must_succeed(result, f"silence trim scene {index + 1}")
        padded_voices.append(padded)

    raw_audio = output_dir / "audio-premix.wav"
    audio = output_dir / "audio-mix.wav"
    scene_count = len(scenes)
    concat_inputs = "".join(f"[{i}:a]" for i in range(scene_count))
    graph = (
        f"{concat_inputs}concat=n={scene_count}:v=0:a=1[vo];"
        f"[{scene_count}:a]volume=0.055,tremolo=f=0.12:d=0.6[pad1];"
        f"[{scene_count + 1}:a]volume=0.028,tremolo=f=0.10:d=0.55[pad2];"
        "[vo][pad1][pad2]amix=inputs=3:duration=first:normalize=0[mix]"
    )
    audio_command = [FFMPEG, "-hide_banner", "-loglevel", "error", "-n"]
    for voice in padded_voices:
        audio_command.extend(["-i", str(voice)])
    audio_command.extend([
        "-f", "lavfi", "-t", str(duration_seconds), "-i", f"sine=frequency=110:sample_rate=48000:duration={duration_seconds}",
        "-f", "lavfi", "-t", str(duration_seconds), "-i", f"sine=frequency=164.81:sample_rate=48000:duration={duration_seconds}",
        "-filter_complex", graph, "-map", "[mix]", "-t", str(duration_seconds), "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(raw_audio),
    ])
    _must_succeed(_run(audio_command, timeout=900), "voice and local synth mix")
    first_pass = _run([
        FFMPEG, "-hide_banner", "-loglevel", "info", "-i", str(raw_audio), "-af",
        "loudnorm=I=-16:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-",
    ], timeout=900)
    _must_succeed(first_pass, "EBU R128 normalization analysis")
    metrics_match = re.search(r"\{\s*\"input_i\".*?\}", first_pass.stderr, re.S)
    if not metrics_match:
        raise RuntimeError("FFmpeg loudnorm analysis returned no measurement JSON")
    loudness = json.loads(metrics_match.group(0))
    metric_names = ("input_i", "input_lra", "input_tp", "input_thresh", "target_offset")
    try:
        metrics = {name: float(loudness[name]) for name in metric_names}
    except (KeyError, TypeError, ValueError) as exc:
        raise RuntimeError("FFmpeg loudnorm analysis returned incomplete measurements") from exc
    if not all(math.isfinite(value) for value in metrics.values()):
        raise RuntimeError("FFmpeg loudnorm analysis returned non-finite measurements")
    normalization_filter = (
        "loudnorm=I=-16:TP=-1.5:LRA=11:"
        f"measured_I={metrics['input_i']:.2f}:measured_LRA={metrics['input_lra']:.2f}:"
        f"measured_TP={metrics['input_tp']:.2f}:measured_thresh={metrics['input_thresh']:.2f}:"
        f"offset={metrics['target_offset']:.2f}:linear=true:print_format=summary"
    )
    normalized = _run([
        FFMPEG, "-hide_banner", "-loglevel", "error", "-n", "-i", str(raw_audio), "-af",
        normalization_filter, "-ar", "48000", "-ac", "2", "-c:a", "pcm_s16le", str(audio),
    ], timeout=900)
    _must_succeed(normalized, "two-pass EBU R128 normalization")
    with wave.open(str(audio), "rb") as wav:
        audio_duration = round(wav.getnframes() / wav.getframerate(), 3)
        if abs(audio_duration - duration_seconds) > 0.05:
            raise RuntimeError(f"mixed audio duration is {audio_duration}, expected {duration_seconds} seconds")

    subtitles = output_dir / "captions.ass"
    _write_subtitles(scenes, subtitles)
    video = output_dir / f"{campaign_id}_rendered.mp4"
    video_inputs: list[str] = [FFMPEG, "-hide_banner", "-loglevel", "error", "-n"]
    for frame in frames:
        video_inputs.extend(["-loop", "1", "-framerate", str(FPS), "-t", str(scene_seconds), "-i", str(frame)])
    filter_nodes = []
    for index in range(scene_count):
        filter_nodes.append(
            f"[{index}:v]zoompan=z='min(zoom+0.00018,1.08)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps={FPS},setsar=1[v{index}]"
        )
    concat = "".join(f"[v{index}]" for index in range(scene_count)) + f"concat=n={scene_count}:v=1:a=0,"
    filter_nodes.append(f"{concat}subtitles=filename='{_filter_path(subtitles)}':force_style='FontName=Noto Sans Thai,FontSize=42,Outline=2,Shadow=0.8,Alignment=2,MarginV=260'[vout]")
    video_inputs.extend([
        "-i", str(audio), "-filter_complex", ";".join(filter_nodes), "-map", "[vout]", "-map", f"{scene_count}:a",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", "-r", str(FPS),
        "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", "-t", str(duration_seconds), str(video),
    ])
    _must_succeed(_run(video_inputs, timeout=2400), "FFmpeg local render")

    probe = _run([
        FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(video),
    ], timeout=60)
    _must_succeed(probe, "ffprobe verification")
    probe_data = json.loads(probe.stdout)
    video_stream = next((item for item in probe_data.get("streams", []) if item.get("codec_type") == "video"), None)
    audio_stream = next((item for item in probe_data.get("streams", []) if item.get("codec_type") == "audio"), None)
    duration = float(probe_data.get("format", {}).get("duration", 0))
    if not video_stream or not audio_stream or video_stream.get("width") != 1080 or video_stream.get("height") != 1920 or abs(duration - duration_seconds) > 0.5:
        raise RuntimeError(f"render verification failed: expected {duration_seconds} seconds, 1080x1920 video, and audio")
    audio_measurement = _measure_ebur128(video)
    if abs(audio_measurement["integrated_lufs"] - (-16.0)) > 0.5:
        raise RuntimeError("render verification failed: integrated loudness is outside -16.0 LUFS ±0.5 LU")
    if audio_measurement["true_peak_dbtp"] > -1.5:
        raise RuntimeError("render verification failed: true peak exceeds -1.5 dBTP")

    return {
        "status": "completed",
        "execution_mode": "local_ffmpeg_cli",
        "visual_engine": "Three.js via pdoom-video dependencies",
        "audio_engine": "Piper local Thai TTS",
        "media_rights_status": "human_confirmation_required",
        "voice_model_license": model_license,
        "local_only": True,
        "network_used": False,
        "synthetic_inputs_only": True,
        "silence_removal": {"threshold_db": -35, "minimum_seconds": 0.4},
        "audio_target": {"standard": "EBU_R128", "lufs": -16.0, "true_peak_dbtp": -1.5, "normalizer": "loudnorm two-pass"},
        "audio_measurement": audio_measurement,
        "caption_timing": "scene-level from supplied script; no word-level alignment",
        "fps": FPS,
        "scene_count": len(frames),
        "scene_seconds": scene_seconds,
        "duration_seconds": round(duration, 3),
        "audio_duration_seconds": audio_duration,
        "video": {
            "path": str(video),
            "bytes": video.stat().st_size,
            "sha256": _sha256(video),
            "codec": video_stream.get("codec_name"),
            "width": video_stream.get("width"),
            "height": video_stream.get("height"),
            "frame_rate": video_stream.get("avg_frame_rate"),
        },
        "audio_mix": {
            "path": str(audio),
            "bytes": audio.stat().st_size,
            "sha256": _sha256(audio),
            "codec": "pcm_s16le",
            "sample_rate": audio_stream.get("sample_rate"),
            "channels": audio_stream.get("channels"),
        },
        "audio": {
            "path": str(video),
            "stream_index": audio_stream.get("index"),
            "codec": audio_stream.get("codec_name"),
            "sample_rate": audio_stream.get("sample_rate"),
            "channels": audio_stream.get("channels"),
            "muxed_in_video": True,
        },
        "frames": [str(frame) for frame in frames],
        "voice_segments": voice_reports,
    }


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        result = render(payload)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "failed", "error": type(exc).__name__, "message": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
