# News Watchlist — แหล่งข่าวรายแผนก

> กติกา: `news_daily` ดึงเฉพาะแถว `✅ active` · โหมด `rss` เร็ว (ไม่กิน Chromium เลย) · `web` ต้อง render JS
> แก้รายการนี้ได้เลย — Owner เพิ่ม/ลบแหล่งข่าวได้เอง (ไม่ต้องแตะโค้ด)
>
> ทุก URL ในตารางนี้ผ่านการทดสอบจริงแล้ว (2026-10-20) — ถ้าเพิ่มใหม่ควรทดสอบก่อน

| # | แผนก | ชื่อแหล่ง | URL | โหมด | สถานะ |
|:--|:------|:----------|:---|:-----|:-------|
| 1 | cmo | การตลาดไทย | https://news.google.com/rss/search?q=ธุรกิจไทย+การตลาด&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 2 | cmo | ธุรกิจไทย (ประชาชาติธุรกิจ) | https://www.prachachat.net/feed | rss | ✅ active |
| 3 | cmo | ผู้ประกอบการออนไลน์ | https://news.google.com/rss/search?q=ผู้ประกอบการ+ธุรกิจออนไลน์&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 4 | sales | SME ไทย / ยอดขาย | https://news.google.com/rss/search?q=ยอดขาย+SME+ไทย&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 5 | sales | ธุรกิจไทย | https://news.google.com/rss/search?q=ธุรกิจไทย+ขาย&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 6 | content | เทคโนโลยี / AI | https://news.google.com/rss/search?q=เทคโนโลยี+AI&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 7 | content | เทคโนโลยีโลก (TechCrunch) | https://techcrunch.com/feed/ | rss | ✅ active |
| 8 | product | เทคโนโลยี / ผลิตภัณฑ์ | https://news.google.com/rss/search?q=เทคโนโลยี+ผลิตภัณฑ์&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 9 | product | AI โลก (TechCrunch) | https://techcrunch.com/feed/ | rss | ✅ active |
| 10 | support | ธุรกิจไทย | https://news.google.com/rss/search?q=ธุรกิจไทย&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 11 | ceo | เศรษฐกิจไทย | https://news.google.com/rss/search?q=เศรษฐกิจไทย&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 12 | ceo | ธุรกิจไทย | https://news.google.com/rss/search?q=ธุรกิจไทย+เศรษฐกิจ&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 13 | cfo | การเงิน / เศรษฐกิจ | https://news.google.com/rss/search?q=เศรษฐกิจ+ไทย+การเงิน&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 14 | engineering | เทคโนโลยี / AI | https://news.google.com/rss/search?q=เทคโนโลยี+AI&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |
| 15 | legal | กฎหมาย / ธุรกิจ | https://news.google.com/rss/search?q=กฎหมาย+ธุรกิจ+ไทย&hl=th&gl=TH&ceid=TH:th | rss | ✅ active |

## เพิ่มแหล่งข่าวเอง

| # | แผนก | ชื่อแหล่ง | URL | โหมด | สถานะ |
|:--|:------|:----------|:---|:-----|:-------|
| 16 | ชื่อแผนก | ชื่อแหล่ง | https://... | rss | ⏳ pending |

## โหมด

| โหมด | ใช้เมื่อ | ต้นทุน |
|:--|:--|:--|
| `rss` | เว็บมี RSS/Atom feed | **0 RAM** (HTTP ตรง ไม่ใช้ Chromium) |
| `web` | เว็บต้อง render JS จึงจะมีเนื้อหา | 47.5MB (Chromium ใน container) |

## ปลายทาง

ข่าวจะถูกส่งเข้า facts store → agent ดึงผ่าน Bus

```
key = "news.<แผนก>.<YYYY-MM-DD>"
POST /v1/context  {"agent_id": "cmo-mark", "keys": ["news.cmo.*"]}
```

- แผนกที่รองรับ: `ceo` · `cmo` · `sales` · `content` · `product` · `support` · `engineering` · `cfo` · `legal`
- เก็บข่าวที่เห็นแล้วไว้ที่ `bus/news/seen.json` → ไม่ส่งข่าวเดิมซ้ำ
