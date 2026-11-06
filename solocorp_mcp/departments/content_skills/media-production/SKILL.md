---
id: content-media-production
version: 1.0.0
owner: content
scope: internal-mcp
trigger: video, narration, voiceover, concat, render, audio-repair
---

# Content Media Production Workflow

## Purpose

Produce editable, reviewable video drafts with continuous narration, verified
media timing, explicit voice rights, and no automatic approval or publishing.

## Route Selection

Choose the render path before generating assets and keep one path for the whole
campaign:

| Need | Use | Rule |
|:--|:--|:--|
| Editable multi-track project, captions, voiceover continuity, or re-editing | `render_campaign_with_concat` | Default for launch and story videos. |
| Fast synthetic storyboard preview with six 15-second scenes | `render_campaign_media_local` | Separate one-shot path. Do not feed its MP4, frames, or audio into Concat. |

The local-media renderer invokes FFmpeg directly. That does not mean the Concat
editor was used. The FFmpeg-skill bridge only stores/records a tool plan; it is
not the local FFmpeg executable and does not edit a video.

## Workflow

1. Read the current brief, Content department guidance, project style, and latest
   campaign version. Confirm duration, audience, aspect ratio, source material,
   and intended distribution.
2. Finalize the story and six-scene storyboard before creating audio. For a
   90-second piece, write one narration that tells the whole story from opening
   to close. Set each visual cut and caption to the script timeline, but do not
   split the voice into short scene-level files.
3. Create or refresh `design_audio_experience` for the exact final script. If the
   script changes, refresh the cue sheet and any dependent voiceover.
4. Choose one voice engine and record its provenance, runtime, and license:
   - **ElevenLabs:** a direct user request to create the specified voiceover
     authorizes the credits needed for that narration. Submit the full narration
     in one request. Do not ask for a separate approval prompt, make unrequested
     variants, or repeat a successful generation without a new request.
   - **OmniVoice:** use only when the installed runtime is reachable and the
     reference speaker has consented to voice cloning. The local `voice_clone.py`
     route requires a 3–10 second reference clip and its transcript. Verify the
     actual device before generation; the main Linux CPU path is documented at
     roughly RTF 165 (about 4.1 hours of compute for 90 seconds of speech). Do
     not claim GPU use unless a GPU endpoint actually ran the job. There is no
     OmniVoice-specific Content MCP tool in the current tool contract; a CLI run
     must be recorded as local execution, not as an MCP provider result.
   - **Piper:** use for fast internal drafts when no paid engine is approved.
     Synthesize the complete narration as one file, not one file per scene. The
     available Thai model is marked CC BY-NC-SA 3.0; treat output as
     non-commercial and internal-only until voice/model rights are separately
     confirmed.
5. Measure the generated voice duration. Adjust script pacing or regenerate
   until the spoken story fits the video naturally. Do not stretch speech,
   repeat a sentence, or leave unused scene-length gaps to force a 90-second
   runtime. Keep natural phrase breaths; flag unexplained silence longer than
   one second for review.
6. Keep generated visual and audio inputs under `central_bus/content/`. For
   Concat, pass the generated visual track(s) and one full-length narration
   track to `render_campaign_with_concat`. Start narration at 0 seconds and
   ensure it spans the story; add timed captions from the final script. Include
   `sound_delivery_filename` only when an Earshot stem was actually rendered.
   Do not silently substitute an engine or skip a requested audio stage.
7. Use FFmpeg/ffprobe for supported prep and technical checks: codec, frame
   size, frame rate, runtime, audio presence, and full-file decode. The installed
   FFmpeg build lacks `drawtext`; create captions in Concat or pre-rendered
   assets instead of depending on that filter.
8. Run `sound_review_campaign_audio` on the latest Concat MP4 and its audio
   track. Inspect continuity, cue timing, integrated loudness, true peak, and
   clipping. If a gap or level issue remains, correct the source mix and render
   again before continuing.
9. Run `review_publish_gate` on the exact latest campaign version. Resolve
   source verification, redaction, and rights issues where possible. Keep the
   campaign `review_required` when any check or media-rights confirmation is
   outstanding.
10. Save the verified internal draft and its checksum in the episode folder;
    update the campaign record and append project memory. User-requested draft
    creation does not need a separate approval prompt. Publication checks and any
    explicit publish authorization remain separate. This skill never publishes.

## Continuity Check

Before calling a narration continuous, confirm all of the following:

- The Concat timeline has one voiceover clip starting at 0 seconds, not six
  independent voice clips with scene-sized holes.
- The voiceover file duration and decoded audio reach the end of the narration;
  there is no unintended long silence between visual scene changes.
- The final MP4 duration matches the intended cut, with the voice audible and
  intelligible through the last scene.
- Earshot review is linked to the final MP4 checksum, not an earlier render.

## Stop Conditions

Stop and report the blocker instead of falling back silently when Concat,
OmniVoice, the selected provider, or Earshot fails. Do not call ElevenLabs for
unrequested audio or create extra paid variants. Do not clone a voice without speaker consent.
Do not combine artifacts from `render_campaign_media_local` with the Concat
workflow. Never record human approval or publish as part of rendering.
