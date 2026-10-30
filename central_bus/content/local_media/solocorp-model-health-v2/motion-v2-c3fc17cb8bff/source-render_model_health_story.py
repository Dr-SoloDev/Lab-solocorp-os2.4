#!/usr/bin/env python3
"""Campaign-specific v2 edit: measured phrase timing, original motion UI and local audio.

Usage: python scripts/render_model_health_story.py prepare scripts/media/model_health_v2.json
       node scripts/render_model_health_frames.mjs <edit.json> [--preview]
       python scripts/render_model_health_story.py finish <edit.json>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import wave
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
CONTENT = (ROOT / "central_bus/content").resolve()
FFMPEG = os.environ.get("FFMPEG_BIN") or "ffmpeg"
FFPROBE = os.environ.get("FFPROBE_BIN") or "ffprobe"
RATE = 48000
FPS = 30


def run(command, *, text=None, timeout=900):
    result = subprocess.run(command, input=text, text=True, capture_output=True, cwd=ROOT, timeout=timeout)
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} exit {result.returncode}: {result.stderr[-2000:]}")
    return result


def write_json(path, data):
    with path.open("x", encoding="utf-8") as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2, allow_nan=False)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_wav(path):
    with wave.open(str(path), "rb") as stream:
        if stream.getsampwidth() != 2 or stream.getframerate() != RATE:
            raise ValueError("expected 48 kHz PCM16")
        samples = np.frombuffer(stream.readframes(stream.getnframes()), dtype="<i2").astype(np.float32) / 32768
        return samples.reshape(-1, stream.getnchannels()).mean(axis=1)


def write_wav(path, samples):
    with wave.open(str(path), "wb") as stream:
        stream.setnchannels(samples.shape[1] if samples.ndim == 2 else 1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes((np.clip(samples, -1, 1) * 32767).astype("<i2").tobytes())


def trim_edges(samples):
    active = np.flatnonzero(np.abs(samples) > .002)
    if not len(active):
        raise ValueError("voice phrase has no audible samples")
    pad = int(RATE * .07)
    samples = samples[max(0, active[0] - pad):min(len(samples), active[-1] + pad)]
    edge = min(int(.008 * RATE), len(samples) // 2)
    samples[:edge] *= np.linspace(0, 1, edge)
    samples[-edge:] *= np.linspace(1, 0, edge)
    return samples


def srt_time(seconds):
    total = round(seconds * 1000)
    hours, total = divmod(total, 3600000)
    minutes, total = divmod(total, 60000)
    secs, millis = divmod(total, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def prepare(source):
    story = json.loads(source.read_text(encoding="utf-8"))
    campaign = story["campaign_id"]
    if not re.fullmatch(r"[a-z0-9-]{1,60}", campaign):
        raise ValueError("campaign_id must be a short ASCII slug")
    scenes = story["scenes"]
    if len(scenes) != 6 or any(s["kind"] not in {"status", "split", "probe", "evidence", "alert", "question"} for s in scenes):
        raise ValueError("six storyboard scenes with explicit supported visual kinds are required")
    rights = json.loads((ROOT / "tools/piper/model-rights.json").read_text())
    job = "motion-v2-" + uuid4().hex[:12]
    out = CONTENT / "local_media" / campaign / job
    out.mkdir(parents=True, exist_ok=False)
    voices = out / "voice"
    voices.mkdir()
    write_json(out / "storyboard.json", story)
    write_json(out / "job.json", {"job_id":job,"campaign_id":campaign,"status":"started","provider":"ffmpeg-cli","inputs":"locally synthesized only","created_at":datetime.now(timezone.utc).isoformat()})
    cursor = 0.0
    clips = []
    for index, scene in enumerate(scenes):
        scene["start"] = cursor
        scene["cues"] = []
        cursor += .42
        for number, phrase in enumerate(scene["narration"]):
            if not isinstance(phrase, str) or not 1 <= len(phrase) <= 180:
                raise ValueError("each spoken phrase must contain 1–180 characters")
            raw = voices / f"scene-{index+1:02}-phrase-{number+1:02}-raw.wav"
            cleaned = voices / f"scene-{index+1:02}-phrase-{number+1:02}.wav"
            report = json.loads(run([sys.executable, str(ROOT / "scripts/local_tts_piper.py"), "--output", str(raw), "--license", rights["license"]], text=phrase, timeout=360).stdout)
            run([FFMPEG,"-hide_banner","-loglevel","error","-n","-i",str(raw),"-af","highpass=f=70,atempo=0.96","-ar",str(RATE),"-ac","1","-c:a","pcm_s16le",str(cleaned)])
            audio = trim_edges(read_wav(cleaned))
            duration = len(audio) / RATE
            cue = {"text":phrase,"start":round(cursor,5),"end":round(cursor+duration,5),"voice_duration":round(duration,5),"model_sha256":report["model_sha256"]}
            scene["cues"].append(cue)
            clips.append((cursor, audio))
            cursor += duration + .18
            print(f"voice {index+1}.{number+1}: {duration:.2f}s", file=sys.stderr, flush=True)
        cursor += .52 if index < len(scenes)-1 else 1.1
        cursor = math.ceil(cursor * FPS) / FPS
        scene["end"] = round(cursor,5)
    story.update({"job_id":job,"duration":round(cursor,5),"fps":FPS,"caption_timing":"measured individual TTS phrases; not word-level alignment","voice_license":rights["license"],"commercial_use":rights["commercial_use"],"output_dir":str(out)})
    samples = np.zeros((math.ceil(cursor * RATE), 2), dtype=np.float32)
    speech_seconds = 0.0
    for start, clip in clips:
        offset = round(start * RATE)
        samples[offset:offset+len(clip)] += clip[:,None]
        speech_seconds += len(clip)/RATE
    # Short original synthesized accents at scene transitions; no continuous drone.
    frequencies = [523.25,587.33,659.25,783.99,440.0,523.25]
    for index, scene in enumerate(scenes):
        length = int(RATE * .75)
        t = np.arange(length,dtype=np.float32)/RATE
        note = (.026*np.sin(2*np.pi*frequencies[index]*t)+.009*np.sin(2*np.pi*frequencies[index]*2*t))*np.exp(-7*t)
        note[:480] *= np.linspace(0,1,480)
        offset = round((scene["start"]+.07)*RATE)
        samples[offset:offset+length,0] += note
        samples[offset:offset+length,1] += note*.86
    write_wav(out / "premix.wav", samples)
    story["speech_duration_seconds"] = round(speech_seconds,3)
    story["speech_occupancy"] = round(speech_seconds/cursor,3)
    write_json(out / "edit.json", story)
    entries=[]
    for scene in scenes:
        for cue in scene["cues"]:
            entries.append(f"{len(entries)+1}\n{srt_time(cue['start'])} --> {srt_time(cue['end'])}\n{cue['text']}\n")
    (out / "captions.srt").write_text("\n".join(entries),encoding="utf-8")
    return {"status":"prepared","edit":str(out / "edit.json"),"duration":story["duration"],"speech_occupancy":story["speech_occupancy"],"job_id":job}


def finish(edit_path):
    out = edit_path.parent.resolve()
    if not out.is_relative_to(CONTENT / "local_media"):
        raise ValueError("edit must reside under local_media")
    story = json.loads(edit_path.read_text(encoding="utf-8"))
    audio = out / "audio-mix.wav"
    first = run([FFMPEG,"-hide_banner","-i",str(out / "premix.wav"),"-af","loudnorm=I=-16:TP=-2:LRA=9:print_format=json","-f","null","-"])
    match = re.search(r'\{\s*"input_i".*?\}',first.stderr,re.S)
    if not match: raise RuntimeError("loudnorm returned no measurements")
    values = json.loads(match.group())
    for key in ("input_i","input_tp","input_lra","input_thresh","target_offset"):
        if not math.isfinite(float(values[key])): raise ValueError("invalid loudness measurement")
    filters = f"loudnorm=I=-16:TP=-2:LRA=9:measured_I={values['input_i']}:measured_TP={values['input_tp']}:measured_LRA={values['input_lra']}:measured_thresh={values['input_thresh']}:offset={values['target_offset']}:linear=true"
    run([FFMPEG,"-hide_banner","-loglevel","error","-n","-i",str(out / "premix.wav"),"-af",filters,"-ar",str(RATE),"-ac","2","-c:a","pcm_s16le",str(audio)])
    video = out / "solocorp-model-health-v2.mp4"
    run([FFMPEG,"-hide_banner","-loglevel","error","-n","-i",str(out / "picture.mp4"),"-i",str(audio),"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-t",str(story["duration"]),"-movflags","+faststart",str(video)])
    probe = json.loads(run([FFPROBE,"-v","error","-show_streams","-show_format","-of","json",str(video)]).stdout)
    visual = next(s for s in probe["streams"] if s["codec_type"]=="video")
    sound = next(s for s in probe["streams"] if s["codec_type"]=="audio")
    if (visual["width"],visual["height"],visual["r_frame_rate"])!=(1080,1920,"30/1") or abs(float(probe["format"]["duration"])-story["duration"])>.1:
        raise RuntimeError("final video geometry/timing mismatch")
    measured = run([FFMPEG,"-hide_banner","-i",str(video),"-map","0:a:0","-af","ebur128=peak=true:framelog=quiet","-f","null","-"])
    integrated=float(re.search(r'Integrated loudness:\s+I:\s+([-+0-9.]+)',measured.stderr).group(1))
    peak=float(re.search(r'True peak:\s+Peak:\s+([-+0-9.]+)',measured.stderr).group(1))
    if abs(integrated+16)>.5 or peak>-1.5: raise RuntimeError(f"audio outside delivery limits: {integrated} LUFS, {peak} dBTP")
    run([FFMPEG,"-v","error","-i",str(video),"-f","null","-"],timeout=600)
    result={"status":"completed","job_id":story["job_id"],"campaign_id":story["campaign_id"],"provider":"ffmpeg-cli","execution_mode":"local_cli_motion_design_v2","video":{"path":str(video),"sha256":sha(video),"bytes":video.stat().st_size,"codec":visual["codec_name"],"width":visual["width"],"height":visual["height"],"fps":30,"duration_seconds":float(probe["format"]["duration"])},"audio":{"codec":sound["codec_name"],"sample_rate":sound["sample_rate"],"channels":sound["channels"],"integrated_lufs":integrated,"true_peak_dbtp":peak},"speech_occupancy":story["speech_occupancy"],"caption_timing":story["caption_timing"],"full_decode_check":"passed","voice_license":story["voice_license"],"commercial_use":story["commercial_use"],"publication_status":"review_required","published":False,"external_network_used":False,"synthetic_inputs_only":True}
    write_json(out / "result.json",result)
    return result


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage",choices=["prepare","finish"])
    parser.add_argument("input",type=Path)
    args=parser.parse_args()
    print(json.dumps(prepare(args.input) if args.stage=="prepare" else finish(args.input),ensure_ascii=False))
