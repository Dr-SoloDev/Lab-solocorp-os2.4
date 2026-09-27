# 🖥️ Current Work Machine — บันทึก 2026-09-25 (CEO)

> Single Source of Truth — เครื่องทำงานหลัก (ย้ายมาใหม่)
> Project หลัก: `/data/projects/Lab-solocorp-os2.4` (HDD)

## Identity ✅ rename แล้ว 2026-09-25 ~19:05
- **Hostname ใหม่:** `solocorp-main` ✅ (verified: /etc/hostname + hostname + hostnamectl static/transient = solocorp-main, /etc/hosts 127.0.1.1 = solocorp-main)
- **Hostname เก่า:** `drsolodev-Lenovo-Z580` (ค้างจากเครื่องเก่า — เลิกใช้แล้ว กันสับสนกับ Lenovo Z580 ตัวจริงที่จะทำ Server)
- **Hardware จริง:** Acer TravelMate P643-M (Firmware V2.15, 2013-10-21)
- **Chassis:** laptop 💻
- **User:** drsolodev
- **Machine ID:** 462622f22d8f4dc1836cb593892c2cd7
- **TODO เสนอ Owner:** rename hostname → `solocorp-main` หรือ `solocorp-main` กันสับสน — ✅ Owner อนุมัติ + รันคำสั่งเอง 2026-09-25 สำเร็จ

## OS
- Linux Mint 22.3 (zena) — base Ubuntu 24.04
- Kernel: 7.0.0-31-generic x86_64
- Uptime ตอนตรวจ: 1:15 ชม, load 0.75-1.45 (ปานกลาง)

## CPU
- Intel Core i7-3632QM @ 2.20GHz (Turbo 3.20GHz)
- 4C/8T, Ivy Bridge (2012), L3 6MB, VT-x ✅
- อายุ ~13 ปี — เก๋าแต่ยังไหว

## RAM
- Total 15Gi (~16GB) — Used 3.8G / Avail 11G / Swap 2G (unused)
- สถานะ: เหลือเฟือสำหรับ Bus + Docker + Dev

## Disk
- `/` → /dev/sda2 234G SSD (HS-SSD-E100 256G) — Used 117G / Free 105G (53%)
- `/data` → /dev/sdb1 916G HDD (HGST HTS541010A9E680) — Used 47G / Free 824G (6%) ✅ หลัก
- Project Lab-solocorp-os2.4 = 443M (จิ๊บๆ)
- Rotational check: sda=0 (SSD) ✅, sdb=1 (HDD) ✅ ตรงตาม Owner เข้าใจ

## GPU
- Intel 3rd Gen HD Graphics 4000 (integrated) เท่านั้น
- No NVIDIA — ไม่เหมาะกับ train AI หนัก / LLM local ใหญ่ / render หนัก

## Network
- WiFi wlp3s0: 192.168.1.17/24 UP
- Tailscale: 100.118.218.73 UP ✅ (remote ได้)
- LAN enp4s0: DOWN
- Docker bridges: 172.17-23.x

## Dev Stack
- Python 3.12.3 / Node v24.14.1 / Docker 29.8.1 ✅
- Containers: scrap-pos-web + scrap-pos-db (healthy, port 8080/3307)
- SoloCorp: busd 8099 ✅ + govctl 8765 ✅

## Health
- CPU temp 55-62°C (high 87 / crit 105) — ร้อนนิดๆ ตามวัย laptop แต่ปลอดภัย
- Battery: ถอด/ไม่พบ (ใช้ไฟตรง — ดีสำหรับเปิดยาว)

## 🎯 ระดับศักยภาพ (CEO ประเมิน)
- **Overall: ระดับ C+ (Mid-Low ยุค 2026) — พอใช้ เหลือๆ สำหรับงาน SoloCorp**
- ✅ เหมาะ: Dev, SoloCorp OS (Bus/Gov/Loop), Docker 3-5 ตัว, Web, light server, storage เยอะ
- ⚠️ พอได้แต่ช้า: build ใหญ่, test suite ยาว, video แปลงไฟล์
- ❌ ไม่เหมาะ: AI training, LLM local 7B+, 3D/render หนัก, เกมหนัก
- 💡 จุดแข็งสุด: HDD 824G ว่าง + RAM 16G + Tailscale — เป็น main + archive ได้สบาย
- 📋 แผน Owner: เครื่องนี้ = หลัก, Lenovo Z580 = Server — รับทราบ บันทึกแล้ว
