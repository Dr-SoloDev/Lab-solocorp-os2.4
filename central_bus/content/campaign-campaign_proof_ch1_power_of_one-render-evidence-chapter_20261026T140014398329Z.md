# Chapter 1 Local Render Record — v2

Date: 2026-10-26  
Campaign: `campaign_proof_ch1_power_of_one`  
Source campaign version: `v4`  
Disposition: `llm_generated`; human review required; not approved or published

## Inputs

- Six synthetic 1080×1920 screenshots from the campaign motion demo: `central_bus/content/campaign-campaign_proof_ch1_power_of_one-scene-00.png` through `scene-05.png`.
- ElevenLabs v4 narration: `central_bus/content/campaign-campaign_proof_ch1_power_of_one-voiceover-proof-of-exis_20261026T133743154428Z.mp3`.
- No user footage, stock media, music, or image-generation API output was used.

## Render

- Engine: local FFmpeg CLI, `7.0.2-static`; this is not an `ffmpeg-skill` MCP render.
- Output: `central_bus/content/campaign-campaign_proof_ch1_power_of_one-video-v2.mp4`.
- Video: H.264, 1080×1920, 24 fps, 46.900 seconds.
- Audio: AAC, mono, 48 kHz. Applied a platform delivery target of -16 LUFS integrated, true peak ceiling -1.5 dBTP, and a 0.5-second ending fade.
- Final measured loudness: -16.3 LUFS integrated and -1.1 dBFS true peak (`ebur128`). This is not an EBU R 128 broadcast mix; that standard targets -23 LUFS integrated.
- Final file size: 1,220,790 bytes.
- SHA-256: `6f75ef2130e2a67e3e85280868188329653c77612be722f346bda24e4b7c16b4`.
- Decode check: `ffmpeg -v error -i <output.mp4> -f null -` exited 0 with no decode errors.
- Contact sheet inspected at `/tmp/solocorp-ch1-video-v2-contact.png`; all six scenes appear in sequence with the review-required footer.

The scenes use slow zooms and hard cuts timed to narration pauses. Crossfade was attempted with `xfade`, including after encoding each scene as CFR H.264. The installed build rejected it with `The inputs needs to be a constant frame rate; current rate of 1/0 is invalid`. No crossfade is claimed in the output.

## Paid Provider Record

- The owner explicitly approved use of ElevenLabs credits for this campaign.
- The v4 narration request consumed 233 credits according to the generation checkpoint.
- A read-only account query after generation reported 12,753 characters used of 31,676, with 18,923 remaining.
- No provider request or credit spend occurred during the FFmpeg render.
- The voice ID and API key are intentionally omitted from this evidence file.

## Limits

- The clip has no burned-in subtitles or karaoke timing.
- FFmpeg MCP was not used to render or process this video. Its D2 evidence covers initialize, tool listing, and a read-only check only.
- Concat was not used. The local diagnostic still reports missing `drawtext`, an unresolved FFmpeg patch-status warning, and no Concat executable on `PATH`.
- This artifact is an AI-generated draft. Factual claims, source verification, rights, redaction, and publication approval remain open.
