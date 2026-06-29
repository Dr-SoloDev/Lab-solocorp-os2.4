# Baileys WhatsApp Integration Reference

## Overview

Baileys (`@whiskeysockets/baileys`) is a production-ready TypeScript/JavaScript library for connecting to WhatsApp Web API via WebSocket. It's the go-to choice for building WhatsApp bots and automation without Selenium/browser automation.

**Repository:** https://github.com/WhiskeySockets/Baileys  
**Documentation:** https://baileys.wiki/  
**npm:** `@whiskeysockets/baileys`

---

## Key Advantages Over Alternatives

### vs whatsapp-web-reveng
- ✅ **Send messages** (not just read-only)
- ✅ **Session management** (restore without QR every time)
- ✅ **Production-ready** (not experimental)
- ✅ **Active maintenance** (9.7K stars vs 6.4K, more active community)
- ✅ **TypeScript** with full type safety
- ✅ **Modern stack** (Node.js, not Python 2.7)

### vs Browser Automation (Puppeteer/Selenium)
- ✅ **No browser overhead** (~500MB RAM saved)
- ✅ **Direct WebSocket** (faster, more stable)
- ✅ **Multi-device support** (WhatsApp's official multi-device API)
- ✅ **Pairing code** support (no QR scanning required)

---

## Authentication Methods

### 1. QR Code (Traditional)
```typescript
import makeWASocket from '@whiskeysockets/baileys'

const sock = makeWASocket({
    printQRInTerminal: true
})
// QR code printed to terminal, scan with phone
```

### 2. Pairing Code (No QR Required!)
```typescript
const sock = makeWASocket({
    printQRInTerminal: false
})

if (!sock.authState.creds.registered) {
    const phoneNumber = '66812345678' // without +
    const code = await sock.requestPairingCode(phoneNumber)
    console.log(`Pairing code: ${code}`) // e.g., ABCD-EFGH
    // Enter this code in WhatsApp app
}
```

**Use case:** Server deployments where terminal access for QR scanning is inconvenient.

---

## Session Management (Critical!)

```typescript
import { useMultiFileAuthState } from '@whiskeysockets/baileys'

// Save session to folder
const { state, saveCreds } = await useMultiFileAuthState('auth_info_baileys')

const sock = makeWASocket({ auth: state })

// MUST save on every creds.update
sock.ev.on('creds.update', saveCreds)
```

**Warning:** If you don't save `creds.update`, messages won't be sent correctly and behavior will be unpredictable.

**Custom storage:** You can implement custom `AuthState` for SQL/NoSQL databases instead of file storage.

---

## Sending Messages

### Basic Text
```typescript
await sock.sendMessage(jid, { text: 'สวัสดีครับ' })
```

### Rich Formats
```typescript
// Image with caption
await sock.sendMessage(jid, {
    image: { url: './photo.jpg' },
    caption: 'ดูรูปนี้'
})

// Reply/Quote
await sock.sendMessage(jid, 
    { text: 'ตอบกลับ' }, 
    { quoted: originalMessage }
)

// Mention
await sock.sendMessage(jid, {
    text: '@66812345678 มาดูหน่อย',
    mentions: ['66812345678@s.whatsapp.net']
})

// Reaction
await sock.sendMessage(jid, {
    react: {
        text: '❤️',
        key: message.key
    }
})

// Poll
await sock.sendMessage(jid, {
    poll: {
        name: 'ชอบอะไร?',
        values: ['ข้อ 1', 'ข้อ 2', 'ข้อ 3'],
        selectableCount: 1
    }
})
```

### JID Format (Chat Identification)
- **Individual:** `66812345678@s.whatsapp.net` (country code + number)
- **Group:** `49123456789-1509911919@g.us` (creator + timestamp)
- **Broadcast:** `1509911919@broadcast` (timestamp only)

---

## Event Handling

```typescript
// Connection management
sock.ev.on('connection.update', (update) => {
    const { connection, lastDisconnect } = update
    
    if (connection === 'close') {
        const shouldReconnect = 
            (lastDisconnect.error as Boom)?.output?.statusCode !== 
            DisconnectReason.loggedOut
        
        if (shouldReconnect) {
            connectToWhatsApp() // Reconnect
        }
    } else if (connection === 'open') {
        console.log('Connected!')
    }
})

// Incoming messages
sock.ev.on('messages.upsert', async ({ messages }) => {
    for (const m of messages) {
        if (m.key.fromMe) continue // Ignore own messages
        
        const text = m.message?.conversation || ''
        const from = m.key.remoteJid
        
        // Handle message
        await sock.sendMessage(from, { text: 'ได้รับแล้วครับ' })
    }
})

// Save credentials on update (CRITICAL!)
sock.ev.on('creds.update', saveCreds)
```

---

## Use Cases for Secondhand POS

### 1. Real-time Lot Sale Notification
**Trigger:** When SO (Sales Order) linked to PO (Purchase Order) is completed
**Action:** Send WhatsApp notification with profit/loss analysis

```typescript
// hooks/after-sale-complete.php
async function onLotSaleComplete(saleData) {
    const profit = saleData.salePrice - saleData.purchasePrice
    const profitMargin = ((profit / saleData.purchasePrice) * 100).toFixed(2)
    
    const message = `
💚 *ขาย LOT สำเร็จ!*
📦 LOT: ${saleData.lotNumber}
💰 กำไร: ${profit.toLocaleString('th-TH')} ฿ (${profitMargin}%)
⏱️ อยู่ในคลัง: ${saleData.daysInInventory} วัน
    `.trim()
    
    await sock.sendMessage(ownerJid, { text: message })
}
```

### 2. Daily Purchase Report (Cron Job)
**Schedule:** Every day at 20:00
**Content:** Summary of all POs for the day

```typescript
// cron: 0 20 * * *
async function sendDailyPurchaseReport() {
    const report = await generateDailyReport()
    
    const message = `
📊 *สรุปยอดรับซื้อประจำวัน*
💰 รวม: ${report.totalAmount.toLocaleString('th-TH')} ฿
📋 จำนวน PO: ${report.totalPOs} รายการ
🏪 สาขาที่รับซื้อเยอะสุด: ${report.topBranch}
    `.trim()
    
    await sock.sendMessage(ownerJid, { text: message })
}
```

### 3. Customer Order Notifications
```typescript
// Notify customer when order is ready
await sock.sendMessage(customerJid, {
    text: `สวัสดีครับคุณ${name}\n` +
          `ออเดอร์ #${orderId} พร้อมส่งแล้วครับ 📦`
})
```

### 4. Interactive Commands
```typescript
sock.ev.on('messages.upsert', async ({ messages }) => {
    const m = messages[0]
    const text = m.message?.conversation || ''
    const from = m.key.remoteJid
    
    // Owner commands
    if (from === ownerJid) {
        switch(text.toLowerCase()) {
            case 'ยอดขายวันนี้':
                const sales = await getTodaySales()
                await sock.sendMessage(from, {
                    text: `💰 ${sales.toLocaleString('th-TH')} ฿`
                })
                break
                
            case 'สต็อกต่ำ':
                const lowStock = await getLowStockItems()
                await sock.sendMessage(from, {
                    text: `⚠️ สินค้าใกล้หมด:\n${lowStock.join('\n')}`
                })
                break
        }
    }
})
```

---

## Architecture Pattern

### Recommended Structure for POS Integration

```
pos-project/
├── backend/                    # Existing PHP POS
│   ├── hooks/
│   │   └── webhook-trigger.php # Trigger WhatsApp notifications
│   └── api/
│       └── whatsapp-webhook.php # Receive triggers from PHP
│
├── services/
│   └── whatsapp/              # Separate Node.js service
│       ├── src/
│       │   ├── baileys/
│       │   │   └── client.js   # Socket connection
│       │   ├── notifications/
│       │   │   ├── lot-sale.js
│       │   │   └── daily-report.js
│       │   ├── cron/
│       │   │   └── jobs.js
│       │   └── server.js       # Express API
│       ├── auth_info_baileys/  # Session storage
│       └── package.json
```

**Communication flow:**
```
PHP Backend → HTTP POST → Node.js Service → Baileys → WhatsApp
```

---

## Installation & Setup

```bash
# 1. Install Baileys
npm install @whiskeysockets/baileys

# 2. Install dependencies
npm install qrcode-terminal  # For QR display
npm install @hapi/boom        # For connection error handling

# 3. First run - authenticate
node src/connect.js
# → Scan QR code or enter pairing code

# 4. Session saved to auth_info_baileys/
# Future runs will auto-restore session
```

---

## Common Pitfalls

### 1. Not Saving Credentials
```typescript
// ❌ Wrong - will break
const sock = makeWASocket({ auth: state })
// No creds.update listener

// ✅ Right
sock.ev.on('creds.update', saveCreds)
```

### 2. Blocking Event Loop
```typescript
// ❌ Wrong - blocks other messages
sock.ev.on('messages.upsert', async ({ messages }) => {
    await heavyOperation() // 10 seconds
})

// ✅ Right - queue for background processing
sock.ev.on('messages.upsert', async ({ messages }) => {
    queue.add({ messages })
})
```

### 3. Not Handling Reconnection
```typescript
// ❌ Wrong - dies on disconnect
sock.ev.on('connection.update', () => {})

// ✅ Right - auto-reconnect
sock.ev.on('connection.update', (update) => {
    if (update.connection === 'close' && shouldReconnect) {
        setTimeout(connectToWhatsApp, 5000)
    }
})
```

---

## Security Considerations

1. **Session Files:** `auth_info_baileys/` contains credentials - add to `.gitignore`
2. **API Keys:** Store POS API keys in environment variables
3. **Webhook Auth:** Use API key or JWT for PHP → Node.js webhooks
4. **Rate Limiting:** WhatsApp has rate limits - queue messages
5. **Owner JID:** Store securely, verify before executing commands

---

## Testing

```typescript
// Unit test example
import { generateLotSaleMessage } from './notifications/lot-sale.js'

test('formats profit message correctly', () => {
    const data = {
        lotNumber: 'LOT-001',
        profit: 5000,
        purchasePrice: 20000,
        daysInInventory: 7
    }
    
    const message = generateLotSaleMessage(data)
    
    expect(message).toContain('LOT-001')
    expect(message).toContain('5,000')
    expect(message).toContain('25.00%')
})
```

---

## Monitoring

Essential metrics:
- Message send success rate
- Connection uptime
- Reconnection frequency
- Message queue depth
- Average response time

Use logging:
```typescript
import pino from 'pino'

const logger = pino({ level: 'info' })

sock.ev.on('messages.upsert', () => {
    logger.info('Message received')
})
```

---

## Resources

- **Official Docs:** https://baileys.wiki/
- **API Reference:** https://baileys.wiki/docs/api/
- **Discord Community:** https://discord.gg/WeJM5FP9GG
- **GitHub Issues:** https://github.com/WhiskeySockets/Baileys/issues
- **Example Code:** See `Example/example.ts` in repo

---

## Session Source

Based on analysis session where user requested detailed Baileys documentation for Phase 2 POS integration (2026-06-13). Includes real-world use cases for secondhand shop notification system.

---

**Status:** Production-ready  
**Complexity:** Medium (Node.js + WebSocket + async patterns)  
**Estimated Setup Time:** 2-4 hours  
**Maintenance:** Baileys handles protocol updates automatically
