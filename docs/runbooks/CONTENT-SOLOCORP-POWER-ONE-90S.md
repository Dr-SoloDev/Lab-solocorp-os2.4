# SoloCorp OS — The Power of One (90s)

## Scope

Creates a vertical Thai internal-review video from six 15-second scenes. The
user-supplied concept was adapted to repository evidence: 18 departments is
supported; an unsupported “20 profiles” count was removed; the MIT license is
described as applying to source code only; specialist count is not stated.

Original Canvas2D motion graphics demonstrate solo workload, Control Layer / Bus,
department ownership, local media work, the real R1–R5 gate meanings, and an
open-question finish. Thai captions are timed to individual synthesized voice
phrases. They are not word-aligned karaoke captions.
Audio uses short original synthesized transition accents; no continuous music bed
or licensed music/SFX package is included.

## Reproduce

From the repository root:

```bash
source .venv/bin/activate && export PYTHONPATH=.
python scripts/render_model_health_story.py prepare scripts/media/solocorp_power_one_90s.json
```

Use the new `edit.json` path printed by `prepare`:

```bash
node scripts/render_model_health_frames.mjs /absolute/path/to/edit.json --preview
node scripts/render_model_health_frames.mjs /absolute/path/to/edit.json
python scripts/render_model_health_story.py finish /absolute/path/to/edit.json
```

Preview images and caption checks are saved in the job directory. Each run uses
a new directory under `central_bus/content/local_media/` and refuses to overwrite
an existing final MP4. Local Piper, Chrome/Playwright, FFmpeg, and Noto Sans Thai
must be installed. The media renderer blocks external browser requests.

## Completed run (2026-10-30)

- Job: `motion-v2-637c4db2e931`; six 15-second scenes; 2,700 motion frames.
- MP4: `central_bus/content/local_media/campaign_solocorp_os_1pt5m_narrative/motion-v2-637c4db2e931/campaign_solocorp_os_1pt5m_narrative-rendered.mp4`.
- H.264/AAC, 1080×1920, 30 fps, 90 seconds, 48 kHz stereo; -16.0 LUFS,
  -4.2 dBTP; full decode passed; speech occupancy 75.3%.
- Twenty-four caption phrases passed the two-line layout check; widest measured
  line is 849 px within the 850 px check bound.
- Video SHA-256:
  `b5a27f313000999c6d828ff68042f4aeb8a06e042d28ffd39d455f63a56bdebd`.
- Job/result records: `campaign-solocorp-power-one-v2-render-job-complete_20261030T012641505704Z.json`
  and `campaign-solocorp-power-one-v2-render-result_20261030T012641541230Z.json`.
- The FFmpeg-skill v2.17.1 manifest at
  `campaign-campaign_solocorp_os_1pt5m_narrative-ffmpeg-job-ffmpeg_20261030T012617209693Z.json`
  is a validated call plan only (`not_started`); the actual render used local
  FFmpeg CLI. No Concat binary or MCP endpoint is available in this runtime, so
  Concat did not execute.

## Rights and review

- Piper `th_TH-tsync2-medium` is CC-BY-NC-SA-3.0 and non-commercial only. Keep
  this render internal until a suitable voice/media license is cleared.
- The campaign gate at v23 is `review_required`, `gate_passed: false`, and has
  no approved version. Primary content, visual prompt, current-script audio cue,
  references, R2, R3, and R5 pass. Source verification, rights, redaction, R1,
  and R4 remain open in the accumulated campaign history.
- No human approval or publication was recorded. D3/D4 and independent audio
  review remain pending.
