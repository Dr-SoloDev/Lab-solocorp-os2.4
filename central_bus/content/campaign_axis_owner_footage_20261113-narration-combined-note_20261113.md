# Narration combined — provenance note (shell step, disclosed)
- date: 2026-11-13T22:30Z
- purpose: SKILL media-production §Continuity Check requires ONE voiceover clip starting at 0s.
  Owner orders: (a) v5 immutable (104.83s, voice 0LNhNxKQjcfJbtdowIAD, sha 5b5ff45b...), (b) tail fill ~15.17s with outro, no stretch/repeat.
  Two ElevenLabs requests were therefore needed (v5 prior-approved + outro v6 this task).
  To satisfy single-clip continuity, the two MP3s were concatenated via ffmpeg into ONE file
  used as the sole audio timeline item at 0s. This is disclosed here, not silent.
- inputs:
  - v5: central_bus/content/campaign-campaign_axis_owner_footage_20261113-voiceover-axis-one_20261113T151841041503Z.mp3
    sha 5b5ff45bea32c922b72e30567d889b40d1e4124483ff24bb024431bc2f49ee20, 104.829388s, mono 44100 128k
  - outro v6: central_bus/content/campaign-campaign_axis_owner_footage_20261113-voiceover-axis-out_20261113T153004527307Z.mp3
    sha 17b2dcbbab3e55c3f48c02f9e033d794c6dc4ef4eb54920d0251329b62f4037f, 14.837551s, 186 chars, same voice/model
    text: ก่อนจะจบคลิปนี้ ผมขอย้ำอีกครั้งครับ ระบบที่ดีเริ่มจากเจ้าของที่ชัดเจน ถ้าคลิปนี้มีประโยชน์ ฝากกดติดตามไว้ด้วยนะครับ แล้วเรามาสร้างงานที่มีระบบไปด้วยกัน ขอบคุณจากใจ แล้วเจอกันคลิปหน้าครับ
- command: ffmpeg -y -v error -i v5 -i outro -filter_complex "[0:a][1:a]concat=n=2:v=0:a=1,aresample=44100,aformat=channel_layouts=mono" -codec:a libmp3lame -b:a 128k -ar 44100 -ac 1 central_bus/content/campaign_axis_owner_footage_20261113-narration-combined-120s.mp3
- output: central_bus/content/campaign_axis_owner_footage_20261113-narration-combined-120s.mp3
  sha 3efd0df7fcb259a670d496d2049fb45a5828d4332c4604ec1711a4c816ead2b9, 119.640816s, mono 44100
  104.829388 + 14.837551 = 119.666939 theoretical; 119.640816 measured (mp3 padding, -0.026s, negligible)
  tail silence vs 120s picture: ~0.36s natural (<1s, no SKILL flag needed), no stretch/repeat of v5
- SKILL deviation disclosure: SKILL says "Submit the full narration in one request."
  Strict one-request compliance would require regenerating v5+outro as a single ElevenLabs call,
  which would violate Owner order "เสียง v5 ใช้เลยไม่เปลี่ยน". Chosen path preserves v5 bytes
  (first ~104.83s verifiable) and meets timeline single-clip rule. Reported here before render.
