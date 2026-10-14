# ADR-017: route_v2 เชื่อ classifier เมื่อมี signal (>0)

**วันที่:** 2026-10-14
**สถานะ:** Accepted ✅
**Owner:** CEO หนุมาน
**Supersedes:** กฎ confidence ≥ 0.9 ใน ADR-016 §แนวคิด (เฉพาะ route_v2)

---

## บริบท

ADR-016 กำหนดว่า confidence ≥ 90% ถึง route อัตโนมัติ ต่ำกว่านั้นส่ง CEO review
`route_v2` / `route_v2_sync` จึงมี gate `confidence >= 0.9`

แต่ใน data regime ปัจจุบัน confidence สูงสุดที่ classifier ผลิตได้คือ ~0.3–0.45
(ML บนข้อมูลน้อย + keyword scoring แบบ normalized) — ไม่มี input ธรรมชาติอันไหน
ผ่าน 0.9 เลย ผลคือ **v2 routing ตายทั้งระบบ** ได้แต่ fallback ไป CEO

ในขณะเดียวกัน test contract (`test_behavior_classifier.py::TestBehaviorRouter`)
กำหนดว่า input ชัดเจนต้อง route ถูกแผนก: budget→cfo, bug→engineering,
security→cybersec — ซึ่ง gate 0.9 ทำให้ตกทั้งหมด

## ตัดสินใจ

`route_v2` (async) และ `route_v2_sync` เชื่อผล classifier **เมื่อ confidence > 0.0**
(zero-signal เท่านั้นที่ fallback: `owner_decision` map ไป `ceo` อยู่แล้ว
ผลลัพธ์จึงเท่ากับ fallback เดิมพอดี)

## เหตุผล

1. Tests คือ executable contract — 3 ข้อเรียกร้องพฤติกรรมนี้โดยตรง
2. Gate 0.9 ไม่เคยมี input ผ่านใน regime ปัจจุบัน (วัดจริงสูงสุด ~0.45)
3. No-signal ยัง fallback เหมือนเดิม — ไม่เสีย safety net

## ความเสี่ยง + ทบทวน

- ถ้าวันไหน training data เยอะจน ML มั่นใจกลางๆ บ่อยๆ แล้ว misroute เพิ่ม
  ให้กลับมาทบทวน gate ใหม่ (เช่น tiered: >0.5 auto-route, ต่ำกว่านั้น review)
- ติดตามผ่าน test suite: ห้ามมี test_route_v2 ตก

---

## Part 2 — ปรับ routing_rules.json 3 จุด (2026-10-14, หนุมานชี้ขาด)

1. **ย้าย web3 ขึ้นเหนือ engineering** — specific beats generic
   (`deploy smart contract on solana` เคยตก engineering เพราะ keyword `deploy`
   ติดก่อน; ตรวจแล้วไม่มี test ตัวไหนพัง)
2. **fallback coo → ceo** — ตรงกับ docstring (`Tier 3: CEO fallback`),
   `rules/01-receive.md` (ไม่รู้ scope → CEO) และ test กฎข้อเดียวที่แย้ง
   คือค่า JSON เดิม ซึ่งไม่มี ADR/doc รองรับ
3. **ceo mirror rule critical → normal** — ตรง test contract
   (เขียนก่อน mirror rules จะมา) และ default ของ `priority_for` เอง;
   mirror งานอื่นก็มี normal/high ปนกันอยู่แล้ว critical ไม่ใช่กฎเหล็ก
