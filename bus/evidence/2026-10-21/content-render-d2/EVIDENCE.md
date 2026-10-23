# D2 Evidence — `scripts/content_render.py` (content-creator-sek)

**ตอบ issue:** [Dr-SoloDev#20](https://github.com/Dr-SoloDev/Lab-solocorp-os2.4/issues/20)
**ผู้รัน:** หนุมาน (ดาริน · darinsupanikorn-rgb) — Windows · RTX 4050
**วันที่:** 23 ต.ค. 2026
**สาขา:** `dispatch/2026-10-23-content-render-d2` (จาก upstream `main` @ `2d24777`)
**โค้ดที่รัน:** `scripts/content_render.py` — **ไม่ได้แก้** (ตามขอบเขต issue)

---

## 1. หลักฐานการรันจริง

```
คำสั่ง :
  set CONCAT_BIN=C:/Users/Lenovo/AppData/Local/Programs/Concat/concat.exe
  set PYTHONIOENCODING=utf-8
  python scripts/content_render.py scripts/specs/thokchai-001.windows.json

exit   : 0

stdout (ครบ) — ดู run-stdout.txt:
[1/6] project_create -> thokchai-001
{
  "steps": [
    "project_create",
    "background",
    "font",
    "cards=11",
    "sounds=11"
  ],
  "clip_count": 11,
  "export": {
    "state": "done",
    "frames": 1980,
    "width": 1080,
    "height": 1920,
    "output": "thokchai-001/export/thokchai-001.mp4",
    "bytes": 674528
  },
  "seconds": 58.1
}
CONTENT_RENDER_OK

stderr (ว่างเปล่า) — ดู run-stderr.txt (0 ไบต์)
```

## 2. ไฟล์ผลลัพธ์

```
path   : thokchai-001/export/thokchai-001.mp4   (relative จาก repo root)
bytes  : 674,528
sha256 : eae33f71ccc6d8777be98f2b4e910e1a97536b6085f7708695ad056dfda15b5c
```

> ไฟล์ mp4 อยู่บนเครื่องหนุมาน (Windows) — ไม่ commit เข้า repo (ขนาด + เป็น output) · พิสูจน์ได้จาก
> `sha256` + `ffprobe-video.json` / `ffprobe-audio.json` ในโฟลเดอร์หลักฐานนี้

## 3. ยืนยันสเปกคลิป (ffprobe)

| ค่า | ได้ | คาดหวัง (issue #20) |
|:--|:--|:--|
| resolution | **1080x1920** | 1080x1920 ✅ |
| fps | **30/1** | 30 fps ✅ |
| duration | **66.000000 s** | < 3 นาที ✅ |
| video codec | h264 | — |
| audio codec | aac 48kHz stereo | — |
| export state | done · frames=1980 | — |

ไฟล์เต็ม: `ffprobe-video.json` · `ffprobe-audio.json`

## 4. สิ่งที่ต้องรู้ (ไม่ใช่บั๊ก — แต่ควรบอก)

1. **สเปก upstream (`scripts/specs/thokchai-001.json`) ใช้ font path ของ Linux**
   (`/usr/share/fonts/truetype/leelawadee/LeelawUI.ttf`) → บน Windows `addFont` จะ fail
   → แก้ใน **spec สาขาตัวเอง**: `scripts/specs/thokchai-001.windows.json`
   (เปลี่ยนเฉพาะ `font.path` → `C:/Windows/Fonts/LeelawUI.ttf` · เนื้อหาอื่นเหมือนเดิมทุกบรรทัด)
   **ไม่ได้แตะ `content_render.py`** — ถือเป็นการ "แก้สเปกในสาขาของตัวเอง" ตามที่ issue อนุญาต
2. ต้องสร้างโฟลเดอร์ `thokchai-001/audio/kit/` + `thokchai-001/export/` ก่อนรัน
   (เสียง kit 4 ไฟล์มาจากคลัง earshot ที่ export ไว้ก่อน: `bell_C5` · `bell_G4` · `tick_1` · `whoosh-short_1`)
3. script พิมพ์เฉพาะ `[1/6]` บน stdout (steps ที่เหลืออยู่ใน JSON ตอนจบ) — พฤติกรรมเดิมของโค้ด ไม่ใช่ error

## 5. ขอบเขตที่ไม่ได้แตะ (ยืนยัน)

- ❌ ไม่แก้ `scripts/content_render.py`
- ❌ ไม่แตะ `profiles/` · `rules/` · `opencode.json` ของ upstream
- ❌ ไม่ rename หัวหน้าแผนกใด ๆ
- ❌ ไม่ลบ `bus/media/creator/` หรือถอน Creator Kit / X
- ✅ เพิ่ม: `scripts/specs/thokchai-001.windows.json` (spec Windows) + หลักฐานในโฟลเดอร์นี้

---

**สรุป:** `content_render.py` รันได้จริงบน Windows + Concat MCP → **exit 0** · mp4 1080x1920@30fps 66s ·
ขอให้ `content-creator-sek` ขยับจาก D0 → **D2** ใน `profiles/CERTIFICATION-REGISTRY.md`
(ผู้ตรวจ = แกนกลาง · ผู้ผลิต ≠ ผู้ตรวจ ตาม SOP-07)

— หนุมาน (CEO · darinsupanikorn-rgb) · 23 ต.ค. 2026
