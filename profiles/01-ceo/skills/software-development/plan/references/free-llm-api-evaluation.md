# Free LLM API Evaluation Pattern

## Overview

When someone shares a free/alternative LLM API endpoint, evaluate whether and how it can be integrated into existing projects.

---

## Evaluation Framework

### 1. API Compatibility Assessment

**Check for OpenAI-compatible format:**
```bash
curl -X POST <endpoint> \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "<model-name>",
    "messages": [{"role":"user","content":"test"}]
  }'
```

**Key indicators:**
- ✅ Endpoint: `/v1/chat/completions` → OpenAI-compatible
- ✅ Standard message format: `{role, content}` array
- ✅ JSON response with `choices[0].message.content`
- ⚠️ Custom format → requires adapter

**Compatibility value:**
- **High:** Drop-in replacement for OpenAI API (just change base URL)
- **Medium:** Same structure but different auth/response format
- **Low:** Completely custom API

---

### 2. Project Architecture Analysis

**Before proposing integration, answer:**

1. **Does the project use LLM/AI currently?**
   - ✅ Yes → Check where (text generation, embeddings, chat)
   - ❌ No → Evaluate if adding AI makes sense

2. **What's the project's primary function?**
   - Text/chat → API directly applicable
   - Video/media → Check if text generation is part of workflow
   - Data processing → Check if AI insights would add value
   - Pure automation → Usually not applicable

3. **Is there a natural integration point?**
   - Content generation
   - User interaction (chatbot)
   - Automated analysis/summarization
   - Configuration generation

---

### 3. Integration Opportunity Matrix

| Project Type | Direct Use | Enhancement Use | Not Applicable |
|-------------|-----------|----------------|----------------|
| **Text/Chat Tool** | ✅ Core feature | Content polish | - |
| **Video/Media** | Script generation | Narration writing | ❌ If tool only records |
| **Documentation** | ✅ Auto-generate | Translation | - |
| **Automation** | Config generation | - | ❌ If purely mechanical |
| **Data Processing** | Insights generation | Report writing | ❌ If only ETL |

---

## Example: MiniMax-M3 + ClawForge Session

### API Provided
```bash
curl -X POST https://xtekky.cc/v1/chat/completions \
  -H "Authorization: Bearer free-m3-by-xtekky" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "MiniMax-M3",
    "messages": [{"role":"user","content":"สวัสดี"}]
  }'
```

**Assessment:**
- ✅ OpenAI-compatible endpoint
- ✅ Free tier available
- ✅ Thai language support (based on example)
- ✅ No personal API key required

### ClawForge Analysis

**Project function:**
```
YAML Script → Playwright → edge-tts → ffmpeg → MP4
```

**Current AI usage:** None - uses hardcoded YAML scripts

**Integration opportunities identified:**

#### 1. ⭐⭐⭐⭐⭐ AI Script Generator
**Where:** New CLI command `clawforge generate`  
**Value:** 80% time savings (no manual YAML writing)  
**Complexity:** Low - single API call to generate YAML

```javascript
async function generateScript(prompt) {
    const response = await axios.post(
        'https://xtekky.cc/v1/chat/completions',
        {
            model: 'MiniMax-M3',
            messages: [
                { role: 'system', content: systemPrompt },
                { role: 'user', content: prompt }
            ]
        },
        {
            headers: {
                'Authorization': 'Bearer free-m3-by-xtekky',
                'Content-Type': 'application/json'
            }
        }
    )
    
    return response.data.choices[0].message.content
}
```

**User flow:**
```bash
# Before
nano demo.yaml  # 30-60 min manual work
clawforge demo.yaml

# After
clawforge generate "demo POS system with login and checkout"
# → AI generates YAML → runs immediately
```

#### 2. ⭐⭐⭐⭐ Narration Enhancement
**Where:** Post-processing of existing YAML  
**Value:** Better-quality narration text  
**Complexity:** Low - text transformation

```javascript
async function enhanceNarration(scene) {
    const prompt = `Rewrite this demo narration to be more engaging and professional:
    "${scene.narration}"`
    
    const response = await callLLM(prompt)
    return response
}
```

#### 3. ⭐⭐⭐ Script Translation
**Where:** Batch processing of existing scripts  
**Value:** Multi-language demos from single source  
**Complexity:** Medium - preserve YAML structure

```bash
clawforge translate demo-en.yaml --to=th --output=demo-th.yaml
```

#### 4. ⭐⭐⭐⭐⭐ Auto Scene Breakdown
**Where:** Analyze website → generate scenes  
**Value:** Automatic demo script from URL  
**Complexity:** High - requires crawling + understanding

```bash
clawforge auto-generate http://localhost:3000 \
  --goal="demo entire POS workflow" \
  --duration=180
```

---

## Integration Decision Tree

```
Free LLM API Provided
    │
    ├─→ Is endpoint OpenAI-compatible?
    │   ├─→ YES: Easy integration ✅
    │   └─→ NO: Need adapter (Medium effort) ⚠️
    │
    ├─→ Does project currently use LLM/AI?
    │   ├─→ YES: Can replace existing provider ✅
    │   └─→ NO: Evaluate new use cases ↓
    │
    └─→ What is project's core function?
        ├─→ Text/Chat: Direct use case ✅
        ├─→ Automation: Check for text generation need
        ├─→ Video/Media: Check for script/narration use
        └─→ Data: Check for insight/report generation
```

---

## Response Pattern

### When Integration Makes Sense

**Structure:**
1. ✅ **Assessment:** "API is OpenAI-compatible"
2. 🎯 **Current State:** "Project X currently does Y without AI"
3. 💡 **Opportunities:** List 3-5 concrete use cases
4. 📊 **Prioritized:** Rank by value/complexity
5. 🛠️ **Implementation:** Show code example for #1 use case
6. 🚀 **Next Steps:** Offer to implement or test

**Example:**
```markdown
## 🔍 Analysis: MiniMax-M3 + ClawForge

### ✅ API Compatible
OpenAI format, free tier, Thai support

### ❌ Direct Use Not Applicable
ClawForge is video generation - doesn't use LLM

### ✅ But Can Add AI Features!

**Top 3 Enhancements:**
1. AI Script Generator (⭐⭐⭐⭐⭐) - 80% time saving
2. Auto Scene Breakdown (⭐⭐⭐⭐⭐) - Full automation
3. Narration Enhancement (⭐⭐⭐⭐) - Quality boost

[Show implementation code]

Want me to implement #1?
```

### When Integration Doesn't Make Sense

**Be direct:**
```markdown
## ❌ Not Applicable

**Why:**
- Project X is [pure automation/data processing/etc]
- No text generation use case
- Adding AI would be feature creep

**Alternative:**
- API would be useful for [different project type]
- Could create wrapper tool for [specific use case]
```

---

## Code Implementation Template

### OpenAI-Compatible Wrapper

```javascript
// src/ai/client.js
import axios from 'axios'

class LLMClient {
    constructor(config) {
        this.endpoint = config.endpoint
        this.token = config.token
        this.model = config.model
    }
    
    async complete(messages, options = {}) {
        try {
            const response = await axios.post(
                this.endpoint,
                {
                    model: this.model,
                    messages,
                    temperature: options.temperature || 0.7,
                    max_tokens: options.maxTokens || 2000
                },
                {
                    headers: {
                        'Authorization': `Bearer ${this.token}`,
                        'Content-Type': 'application/json'
                    }
                }
            )
            
            return response.data.choices[0].message.content
            
        } catch (error) {
            console.error('LLM API Error:', error.message)
            throw new Error(`Failed to get LLM response: ${error.message}`)
        }
    }
}

// Usage
const client = new LLMClient({
    endpoint: 'https://xtekky.cc/v1/chat/completions',
    token: 'free-m3-by-xtekky',
    model: 'MiniMax-M3'
})

const response = await client.complete([
    { role: 'system', content: 'You are a helpful assistant' },
    { role: 'user', content: 'Hello' }
])
```

### Environment Configuration

```bash
# .env
LLM_ENDPOINT=https://xtekky.cc/v1/chat/completions
LLM_TOKEN=free-m3-by-xtekky
LLM_MODEL=MiniMax-M3
```

---

## Pitfalls to Avoid

### 1. ❌ Forcing Integration
Don't add AI just because you can. Must have clear value.

**Red flags:**
- "We could use AI to..." without clear benefit
- Feature would be nice-to-have, not solving pain point
- Adding complexity without proportional value

### 2. ❌ Ignoring Project Architecture
Don't propose solutions that don't fit the stack.

**Example:**
- Pure frontend project → Don't add Node.js backend just for LLM
- PHP project → Consider PHP SDK, not "rewrite in Node.js"
- CLI tool → API should be optional, not required dependency

### 3. ❌ Overestimating Free Tier
Free APIs have limits - rate, quota, availability.

**Always mention:**
- Rate limits
- Uptime SLA (usually none for free)
- Fallback strategy if API becomes unavailable

### 4. ❌ Not Testing First
Always test the API before proposing integration.

```bash
# Test with simple request
curl -X POST <endpoint> \
  -H "Authorization: Bearer <token>" \
  -d '{"model":"...","messages":[{"role":"user","content":"test"}]}'
```

---

## Testing Checklist

Before recommending integration:

- [ ] API call succeeds with sample request
- [ ] Response format matches OpenAI structure (if claimed)
- [ ] Error handling returns useful messages
- [ ] Supports target language (if relevant)
- [ ] Response time acceptable (<5s for typical request)
- [ ] Free tier limits documented or discoverable

---

## Real-World Success Criteria

**Good integration:**
- Solves existing pain point (manual work, slow process)
- Natural fit with project's purpose
- Low implementation complexity (<1 day)
- Clear value measurement (time saved, quality improved)
- Graceful degradation if API unavailable

**Poor integration:**
- Added because "cool" without clear benefit
- Requires architectural changes
- High complexity for marginal benefit
- No fallback if API fails
- Unclear success metrics

---

## Session Context

Pattern emerged from session analyzing MiniMax-M3 free API endpoint in context of ClawForge video generation tool (2026-06-13). User asked for evaluation of whether/how to integrate free LLM API into existing project.

Key insight: **Integration value depends on project's core function, not just API availability.** Always answer "Does this project need text generation?" before proposing how to integrate.
