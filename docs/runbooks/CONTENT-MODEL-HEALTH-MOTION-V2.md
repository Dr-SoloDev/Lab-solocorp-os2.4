# Model Health motion edit V2

Campaign-specific internal-review render. This does not replace the existing
90-second Content MCP renderer and does not certify an autonomous production team.

## Intent and ownership

The previous edit used generic still visuals, production-step headlines, long
captions and substantial padded silence. V2 uses six explicit UI demonstrations,
Thai headlines, phrase-timed captions and deterministic animation at 30 fps.
Sek provides creative direction and an independent visual review; Codex runs the
local tools. Separate specialist execution is not claimed.

## Reproduce

From the repository root, with installed local Piper voice, Chrome, FFmpeg,
Playwright and Noto Sans Thai:

```bash
source .venv/bin/activate && export PYTHONPATH=.
python scripts/render_model_health_story.py prepare scripts/media/model_health_v2.json
```

The command prints a new unique `edit.json` path. Use that exact path in order:

```bash
node scripts/render_model_health_frames.mjs /absolute/path/to/edit.json --preview
node scripts/render_model_health_frames.mjs /absolute/path/to/edit.json
python scripts/render_model_health_story.py finish /absolute/path/to/edit.json
```

Review the six preview PNGs before the full render. The renderer checks every
caption for a maximum of two lines and a width of 850 pixels. Finalization checks
1080×1920, 30 fps, duration, full decoding and final AAC loudness. Expected audio
is -16 LUFS ±0.5 with true peak no higher than -1.5 dBTP.

All generated assets stay under `central_bus/content/local_media/`. Each prepare
run gets a new directory; existing full videos are never overwritten. Intermediate
audio and final artifacts are preserved for inspection. Failed jobs may retain
partial outputs; start a new job rather than deleting unrelated files.

## Evidence and limits

- `edit.json`: actual phrase durations and scene timing, not word alignment.
- `captions.srt`: narration transcript with measured phrase cues.
- `preview-report.json` and `picture-report.json`: layout checks and preview paths.
- `result.json`: final MP4 SHA-256, codec/geometry/timing, loudness and decode result.
- Review contact sheet and independent reviewer report are attached separately.
- UI values are fictional demonstrations, visibly labeled throughout.
- Voice: Piper `th_TH-tsync2-medium`, CC-BY-NC-SA-3.0; details are in
  `tools/piper/model-rights.json`. Commercial rights remain uncleared.
- No paid provider, external-media input, human approval or publication is used.
- Pipeline D3/D4 certification remains pending; a successful render does not
  constitute certification or approval to publish.

## Completed run: 2026-10-30

- Job: `motion-v2-c3fc17cb8bff`; campaign version v7 remains
  `review_required`, with `approved_version: null` and `gate_passed: false`.
- MP4: `central_bus/content/local_media/solocorp-model-health-v2/motion-v2-c3fc17cb8bff/solocorp-model-health-v2.mp4`.
- Output: 63.433 s, H.264/AAC, 1080×1920, 30 fps, 48 kHz stereo,
  -16.0 LUFS, -4.5 dBTP; full decode passed; speech occupancy 84.9%.
- All 18 phrase captions passed the layout check (maximum two lines and 768 px
  measured width). Phrase cues use each WAV's measured duration; they are not
  word-aligned.
- Final six-scene MP4 contact sheet:
  `central_bus/content/local_media/solocorp-model-health-v2/motion-v2-c3fc17cb8bff/final-contact-sheet.png`.
- Sek completed a separate still-preview advisory review recorded at
  `central_bus/content/model-health-v2-sek-preview-review_20261030T003642635883Z.json`.
  It found no blocking visual defect; it flagged small evidence/footer type and
  the fictional `checked_at` value for human review on a phone. Audio and motion
  cadence were not independently reviewed.
- Gate v7 passes primary content, visual prompt, current-script audio cue, supplied
  references, R4, and R5. Source verification, voice/media rights, redaction, R1,
  R2, and R3 remain open. Do not publish until the gate is cleared and a human
  approves the exact campaign version.
