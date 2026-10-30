# Content Creator Story — 60s

## Delivery

- Campaign: `campaign_solocorp_content_creator_60s`
- Story: six 10-second scenes — brief, specialist handoff, unified production, MCP/Central Bus, human review, open CTA.
- Team order shown: Sek leads; Kawee develops the narrative; Film scripts; Art defines visuals; Sound defines audio; Ink checks the Publish Gate.
- Script artifact: `campaign-campaign_solocorp_content_creator_60s-client-generated_20261030T030049668125Z.md` (v8; provenance is client-supplied and unverified).
- Audio cue artifact: `campaign-campaign_solocorp_content_creator_60s-audio-cue-campaig_20261030T030102296672Z.md` (v9).
- Video: `central_bus/content/local_media/campaign_solocorp_content_creator_60s/motion-v2-7b80c8018b1a/solocorp-content-creator-60s.mp4`.
- Specs: 60 seconds, 1080×1920, 30 fps, H.264 video, AAC stereo at 48 kHz; SHA-256 `09c1d1effee909eb7d80ca2bd0bf956ea4968f7f3623a13b97199136c3828ed4`.
- Measured audio: -16.0 LUFS integrated, -3.4 dBTP; phrase-timed Thai Piper voice, locally synthesized warm pad and transition accents.
- Validation: ffprobe geometry and duration passed; full decode passed; local render report has `external_network_used: false`.

## Reproduce

From repository root:

```bash
source .venv/bin/activate
export PYTHONPATH=.
python scripts/render_model_health_story.py prepare scripts/media/content_creator_story_60s.json
node scripts/render_model_health_frames.mjs <printed-edit.json> --preview
node scripts/render_model_health_frames.mjs <printed-edit.json>
python scripts/render_model_health_story.py finish <printed-edit.json>
```

The current renderer uses Canvas2D motion graphics, local Piper TTS and the local FFmpeg CLI. It does not execute ffmpeg-skill or Concat: the skill runtime is pending independent verification, and no Concat executable or MCP endpoint was verified. The ffmpeg-skill manifest is a stored check plan only.

## Review Gate

- ffmpeg-skill check plan: `campaign-campaign_solocorp_content_creator_60s-ffmpeg-job-ffmpeg_20261030T031157527693Z.json`; status `not_started`, automatic execution disabled.
- Publish Gate report: `campaign-campaign_solocorp_content_creator_60s-publish-gate-v11_20261030T031212222088Z.md`.
- Status: `review_required`; `gate_passed: false`; no approval or publication recorded.
- Source verification, media rights and redaction remain for human review. The local `th_TH-tsync2-medium` voice model is CC-BY-NC-SA-3.0 and non-commercial; keep this render internal until usage rights are cleared.
