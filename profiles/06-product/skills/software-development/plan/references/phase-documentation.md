# Phase Documentation Pattern

## Use Case

When the user wants to **document future work** rather than create an execution plan for immediate implementation.

**Signals:**
- "เก็บไว้ Phase 2"
- "ยังไม่ทำในเฟสนี้"
- "อยากเก็บฟีเจอร์นี้ไว้ใช้พัฒนาต่อ"
- "บันทึกข้อมูลเอาไว้"
- User wants to defer implementation but preserve knowledge

**Different from implementation plan:**
- Implementation plan → ready to execute now
- Phase documentation → preserve for later, with business context

---

## Documentation Structure

Create under project's `docs/` directory:

```
docs/
├── phase-N/
│   ├── README.md                    # Overview, goals, timeline
│   ├── <feature>-integration.md     # Technical architecture
│   └── features/
│       ├── <feature-1>.md           # Feature spec + code samples
│       └── <feature-2>.md           # Feature spec + code samples
└── business/
    ├── target-customers.md          # Market analysis
    ├── pricing-model.md             # Pricing strategy
    └── go-to-market.md              # Sales strategy
```

---

## Content Sections

### 1. Technical Feature Documentation

Each feature document should include:

```markdown
# <Feature Name>

## 🎯 Overview
[One paragraph: what it does, why it matters]

## 💡 Business Value
### For Business Owner:
- Benefit 1
- Benefit 2

### For Analysis:
- Insight 1
- Insight 2

## 📊 Data Model
```typescript
interface DataStructure {
    // Complete TypeScript interface
}
```

## 🔔 Flow / Architecture
[Sequence diagram or step-by-step flow]

## 🚀 Implementation
### 1. Trigger Point
```language
// Complete code sample
```

### 2. Data Processing
```language
// Complete code sample
```

### 3. Output / Notification
```language
// Complete code sample
```

## 📱 Examples
[Real examples with actual data]

## 🧪 Testing
[How to test, what to verify]

## 🔄 Future Enhancements (Phase N+1)
[Ideas for later]

---

**Status:** 📝 Ready for Implementation  
**Priority:** ⭐⭐⭐⭐⭐ (1-5 stars)  
**Estimated Time:** X days
```

### 2. Architecture Documentation

```markdown
# <System> Integration

## 🎯 Purpose
[Why integrate this system]

## 🏗️ Architecture
```
[ASCII diagram or description]
Component A → Component B → Component C
```

## 🔧 Technology Stack
- Backend: ...
- Integration library: ...
- Database: ...

## 📂 Project Structure
```
project/
├── services/
│   └── integration-service/
│       ├── src/
│       └── package.json
```

## ⚙️ Configuration
```env
VAR_NAME=value
```

## 🔐 Security
- Authentication: ...
- Secrets management: ...

## 🚀 Deployment
[How to deploy when ready]

## 📊 Monitoring
[What metrics to track]
```

### 3. Business Documentation

```markdown
# Target Customers

## 👥 Customer Segments
### Segment 1: [Name]
**Characteristics:**
- Size: ...
- Pain points: ...
- Willingness to pay: ...

**Persona:**
- Name: ...
- Age: ...
- Tech savvy: ...
- Goals: ...

## 📊 Market Analysis
### TAM (Total Addressable Market)
- Size: X
- Value: Y

### SAM (Serviceable Available Market)
- Size: X
- Value: Y

### SOM (Serviceable Obtainable Market)
- Year 1: X
- Year 3: Y

## 💰 Pricing Strategy
### Tier 1: Starter
**Price:** X ฿/month
- Feature A
- Feature B

### Tier 2: Professional
**Price:** Y ฿/month
- All Starter features
- Feature C
- Feature D

## 🎯 Go-to-Market
### Phase 1: Pilot
- Target: X customers
- Strategy: ...

### Phase 2: Early Adopters
- Target: Y customers
- Strategy: ...
```

---

## Execution Pattern

### 1. Understand Scope
Ask clarifying questions:
- "จะเก็บไว้ Phase ไหน?"
- "ต้องการ technical docs อย่างเดียวหรือรวม business strategy?"
- "มี code samples ที่อยากเห็นไหม?"

### 2. Create Directory Structure
```bash
mkdir -p docs/phase-N/{features,implementation}
mkdir -p docs/business
```

### 3. Write Documents
- Start with overview (README.md)
- Write feature specs with code samples
- Add business docs if requested

### 4. Include Complete Code Samples
**Not just pseudocode** — write production-ready examples:
```typescript
// Complete, runnable code
async function sendNotification(data: NotificationData) {
    const sock = await getWASocket()
    const message = formatMessage(data)
    await sock.sendMessage(recipientJid, { text: message })
}
```

### 5. Commit to Git
```bash
git add docs/
git commit -m "docs: Add Phase N documentation - <summary>"
git push origin main
```

### 6. Summary for User
```markdown
## ✅ เสร็จสมบูรณ์! Phase N Documentation พร้อมใช้งาน

### 📁 สิ่งที่สร้างไว้
- Technical: X, Y, Z
- Business: A, B, C

### 🎯 สิ่งที่ได้
- สำหรับ Phase N: [benefits]
- สำหรับอนาคต: [benefits]

### 📂 Structure
[Tree view of created files]

### 🎉 Next Steps
- ตอนนี้: [focus on current phase]
- หลังส่งมอบ: [read docs and implement]
```

---

## Key Principles

### 1. **Complete, Not Placeholder**
Write full code samples, not TODOs:
```typescript
// ❌ Bad
// TODO: Implement notification logic

// ✅ Good
async function sendNotification(data: LotSaleData) {
    const message = `
💚 *ขาย LOT สำเร็จ!*
📦 ${data.reference_no}
💰 กำไร: ${data.profit.toLocaleString('th-TH')} ฿
    `.trim()
    
    await sock.sendMessage(ownerJid, { text: message })
}
```

### 2. **Production-Ready Examples**
Include error handling, types, real patterns:
```typescript
// Not just happy path — show real implementation
try {
    const result = await apiCall()
    return result
} catch (error) {
    console.error('API call failed:', error)
    throw new Error('Failed to send notification')
}
```

### 3. **Business Context Matters**
Always include:
- **Why** this feature (business value)
- **Who** benefits (personas, pain points)
- **How much** value (ROI, metrics)

### 4. **Future-Proof Structure**
- Use versioned phases (phase-2, phase-3)
- Link related docs
- Mark status and priority

---

## Anti-Patterns

### ❌ Don't Create "Plans" for Future Phases
**Wrong:**
```markdown
# Phase 2 Implementation Plan

Task 1: Setup WhatsApp service
Task 2: Implement notification
Task 3: Test
```

**Right:**
```markdown
# WhatsApp Integration Architecture

[Complete technical documentation with code samples]
```

**Why:** Plans become stale. Documentation stays relevant.

---

## Example Session

**User:** "อยากเก็บฟีเจอร์ WhatsApp notification ไว้ Phase 2 บันทึกไว้ในโปรเจกต์"

**Agent Response:**
1. ✅ Create `docs/phase-2/README.md` (overview)
2. ✅ Create `docs/phase-2/whatsapp-integration.md` (architecture)
3. ✅ Create `docs/phase-2/features/lot-sale-notification.md` (spec + code)
4. ✅ Create `docs/business/target-customers.md` (if relevant)
5. ✅ Commit และ push
6. ✅ สรุปให้ user ว่าสร้างอะไรไว้บ้าง

---

**Last Updated:** 2026-06-13  
**Source Session:** Documentation for POS Phase 2 (WhatsApp + Business Strategy)
