# Web3 Review Criteria — Legal Vault Templates

> **Reviewed by:** อัยวา (Web3 Specialist)  
> **Date:** 2026-07-07  
> **Scope:** 8 templates × Web3/DeFi/blockchain coverage

---

## สรุปภาพรวม

| Template | Assessment |
|:---------|:----------:|
| 1. NDA Mutual | ⚠️ Needs Work |
| 2. NDA One-way | ⚠️ Needs Work |
| 3. Terms of Service | ✅ Pass (strong) |
| 4. Privacy Policy PDPA | ✅ Pass (good) |
| 5. IP Assignment | ⚠️ Needs Work |
| 6. Consulting Agreement | ❌ Gap |
| 7. Customer Agreement B2B | ❌ Gap |
| 8. Advisor Agreement FAST | ✅ Pass (best in class) |

---

## 🔴 Priority 1 — ต้องทำก่อน

### 1. Blockchain Immutability Exception — NDA ทั้งสองฉบับ
**Problem:** ข้อ return/destroy confidential data ขัดกับ blockchain immutability
**Fix:** เพิ่ม carve-out ว่าข้อมูลบน blockchain ไม่สามารถลบ/ส่งคืนได้ ให้ anonymization หรือ access termination แทน

### 2. Smart Contract Open Source Licensing — IP Assignment
**Problem:** IP assignment อาจ conflict กับ open source license (GPL, BUSL, MIT)
**Fix:** เพิ่ม clause สำหรับ smart contract ที่ intend to be open source

### 3. Web3 Cross-reference — Customer Agreement B2B
**Problem:** Customer Agreement ไม่มี Web3 clause ขาด SLA สำหรับ blockchain network conditions
**Fix:** Cross-reference ไป ToS ข้อ 6 เพิ่ม SLA exception สำหรับ blockchain congestion, reorg, gas spike

### 4. Crypto Payment & Smart Contract Deliverables — Consulting Agreement
**Problem:** ไม่มี clause รับ payment เป็น crypto, ไม่ mention gas cost, testnet/mainnet, audit
**Fix:** เพิ่ม optional clause สำหรับ crypto payment และ blockchain-specific deliverables

### 5. TGE Failure & Regulatory Compliance — Advisor Agreement FAST
**Problem:** ไม่มี clause ถ้า TGE ไม่เกิด, ไม่มี compliance representation กับ securities laws
**Fix:** เพิ่ม fallback compensation, regulatory compliance, clawback clause

---

## 🟡 Priority 2 — ควรทำรอบถัดไป

6. **Privacy Policy × Blockchain** — ขยายสิทธิ์ PDPA ที่ไม่สามารถปฏิบัติได้บน blockchain
7. **ToS ข้อ 6** — เพิ่ม MEV/Oracle risk, 3rd party protocol disclaimer
8. **IP Assignment** — เพิ่ม on-chain deployment rights, upgrade rights
9. **NDA Mutual** — ปรับ liability cap ให้สะท้อน DeFi risk profile

---

## Cross-Template Web3 Issue Matrix

| Web3 Issue | NDA-M | NDA-1W | ToS | PDPA | IP | CA | CustA | Adv |
|:-----------|:-----:|:-----:|:---:|:----:|:-:|:-:|:----:|:---:|
| Smart Contract Risk | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ⚠️ |
| Private Key / Wallet | ❌ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Blockchain Immutability | ❌ | ❌ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| On-chain Data ≠ Confidential | ⚠️ | ⚠️ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ |
| Token/Equity Compensation | — | — | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| Token Vesting & Lock-up | — | — | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| DeFi Integration Risk | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ |
| Jurisdiction × DeFi | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ | ❌ | ❌ |
| PDPA × Blockchain | ❌ | ❌ | ⚠️ | ⚠️ | ❌ | ❌ | ❌ | ❌ |
| OSS Licensing | — | — | ❌ | ❌ | ⚠️ | ❌ | ❌ | ❌ |

Legend: ✅ Covered | ⚠️ Partial | ❌ Missing | — N/A

---

## สรุปจากอัยวา

> **ToS ข้อ 6 และ Advisor Agreement FAST** เป็นสอง template ที่ออกแบบมาเพื่อ Web3/DeFi โดยเฉพาะ — ทำได้ดีมาก
>
> **จุดอ่อนหลัก:** ความขัดแย้งระหว่าง Blockchain Immutability กับข้อกำหนดแบบ centralized:
> - Return/destroy confidential data (NDA)
> - IP assignment ที่ไม่兼容 open source licensing
> - SLA ที่ไม่ account blockchain conditions
> - Compensation ที่ไม่มี fallback ถ้า TGE ไม่เกิด
>
> แนะนำให้ **Legal (ตุลย์)** รับ action items #1-#5 ไปดำเนินการ sprint นี้ ปรึกษา external counsel ก่อน deploy
