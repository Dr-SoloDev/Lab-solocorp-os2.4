# PII SCAN — campaign_axis_owner_footage_20261113 — C3
- date: 2026-11-13T22:35Z
- method: ffprobe format_tags (12/12) + strings narrow check + full decode ffmpeg -f null (12/12 OK) + thumbnail skim at 5s per clip (12/12 viewed)
- EXIF/GPS: no exiftool on host; ffprobe format_tags = isom/minor_version/compatible_brands/encoder Lavf62.3.103 only — no GPSPosition/Latitude/Longitude, no location tags, no com.apple/com.android location atoms. Narrow strings check for com.apple.quicktime.location / GPS / location: none found (broad lat/lon 3-char matches are random binary fragments, not atoms).
- audio: AAC mono 24kHz present in all 12 (to be stripped with -an in Concat per plan)
- decode: 12/12 decode OK via ffmpeg null sink
- skim 12/12:
  01 AXIS logo graphic, no person, no text PII
  02 SoloCorp OS laptop + partial side face left edge (likely Owner self) — allowed under Owner consent, no other PII
  03 monitor Human-in-the-Loop/Publish Gate + back of head — no PII
  04 server room hologram — no person, no PII
  05 Department Architecture diagram — no real person
  06 MCP device graphic — no person
  07 AXIS tower + stylized multi-agent graphic — no real person
  08 MAXIMUM POWER dashboard — no person, numbers are fake metrics (98.7%) not PII
  09 desk silhouette from behind + Thai gibberish hologram — back view, not identifiable, no PII
  10 AXIS tower crowd from behind (AI crowd) — no identifiable real person, no plates/docs
  11 close-up Asian man + Permission Wall/Quota-Lock (cinematic AI actor) — no name/doc/number visible, treated as Owner-supplied creative, no external PII
  12 circular drone formation — no person
- verdict: PASS 12/12, no clip cut, no fail. Human Owner to confirm at preview gate (this skim does not replace human approval).
- thumbs: /tmp/opencode/axis_skim_20261113/01..12.jpg (host-local, not committed)
