---
name: ui-animation-review
description: ตรวจสอบและปรับปรุง animation/motion ใน UI codebase — review, audit, plan อิงจาก Emil Kowalski's design engineering philosophy แหล่งความรู้: emilkowalski/skills
argument-hint: "[component / file path / diff to review]"
user-invocable: true
---

# UI Animation Review

> Skill สำหรับตรวจสอบ animation/motion ใน UI codebase  
> อิงจาก Emil Kowalski's animation philosophy (ex-Vercel, ex-Linear)

## เมื่อไรควรใช้ Skill นี้

- เมื่อต้องการ **review animation code** ก่อน merge
- เมื่อมีคนขอ "improve animations" หรือ "make app feel smoother"
- เมื่อต้องการ **audit** ทั้ง codebase หา animation issues
- เมื่อไม่แน่ใจว่า easing/duration ที่เลือกถูกต้องหรือไม่

## วิธีการใช้งาน

### 1. Review Animation Code (Pull Request / Diff)

ตรวจสอบ animation/motion ใน diff โดยใช้ **10 Non-Negotiables**:

| # | ข้อ | เช็ค |
|---|-----|------|
| 1 | **Justified motion** | animation นี้มี purpose หรือ "it looks cool"? |
| 2 | **Frequency-appropriate** | keyboard/100+/day → ไม่ animate |
| 3 | **Responsive easing** | `ease-in` บน UI? → ❌ ใช้ `ease-out` |
| 4 | **Sub-300ms** | >300ms โดยไม่มีเหตุผล? |
| 5 | **Origin-aware** | popover/dropdown scale จาก center? |
| 6 | **Interruptible** | keyframes บน toast/toggle? ใช้ transitions แทน |
| 7 | **GPU-only** | animate `width`/`height`/`margin`? |
| 8 | **Accessibility** | `prefers-reduced-motion`? hover gate? |
| 9 | **Asymmetric timing** | กดช้า ปล่อยเร็วเท่ากัน? |
| 10 | **Cohesion** | animation match component personality? |

**Output format (REQUIRED):** Markdown table Before/After/Why

```markdown
| Before | After | Why |
|--------|-------|-----|
| `transition: all 300ms` | `transition: transform 200ms ease-out` | ระบุ property ที่ต้องการ; `all` animate โดยไม่จำเป็น |
| `ease-in` บน dropdown | `ease-out` + custom curve | `ease-in` เริ่มช้า รู้สึก sluggish |
| `transform-origin: center` | `var(--radix-popover-content-transform-origin)` | Popover ต้อง scale จาก trigger |
```

### 2. Audit Animation Codebase

ใช้เมื่อต้องการ survey ทั้ง codebase สำหรับ animation issues:

**Categories:**
1. Purpose & frequency
2. Easing & duration
3. Physicality & origin (scale(0)? wrong transform-origin?)
4. Interruptibility (keyframes vs transitions)
5. Performance (GPU properties only?)
6. Accessibility (reduced-motion? hover gate?)
7. Cohesion & tokens
8. Missed opportunities

**Commands ที่ grep หา:**
- `transition`, `animation`, `@keyframes` — core animations
- `ease-in`, `ease-out`, `cubic-bezier` — easing issues
- `scale(0)`, `transform: scale(0)` — bad entrances
- `transition: all` — over-broad transitions
- `transform-origin: center` — wrong origin (ยกเว้น modal)
- `width`, `height`, `margin`, `padding`, `top`, `left` — GPU violations
- `prefers-reduced-motion` — missing a11y
- `@media (hover` — missing hover gate

### 3. Improvement Plan Template

เมื่อต้องสร้างแผนปรับปรุง animation:

```markdown
## แผน: [ชื่อสั้น]

**ไฟล์:** `path/to/file.tsx`
**บรรทัด:** L42-L48
**ปัญหา:** [สรุปสั้น]
**Current code:**
```css
.example {
  transition: all 300ms ease-in;
}
```
**Target:**
```css
.example {
  transition: transform 200ms cubic-bezier(0.23, 1, 0.32, 1);
}
```
**Fix type:** [easing / duration / origin / interruptibility / performance / a11y]
**Priority:** [HIGH / MEDIUM / LOW]
**Feel check:** ลองดูใน slow motion / frame-by-frame ว่า easing รู้สึกถูกต้อง
```

## Animation Reference Tables

### Easing Curves (CSS Custom Properties)

```css
/* ใช้ custom cubic-bezier — ห้ามใช้ built-in CSS easings */
--ease-out: cubic-bezier(0.23, 1, 0.32, 1);
--ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
--ease-drawer: cubic-bezier(0.32, 0.72, 0, 1);
```

### Duration Reference

| Element | Duration |
|---------|----------|
| Button press | 100-160ms |
| Tooltip, small popover | 125-200ms |
| Dropdown, select | 150-250ms |
| Modal, drawer | 200-500ms |
| Marketing | ยาวกว่านี้ได้ |
| **UI max** | **300ms** |

### Spring Animation Config

```js
// Apple-style (recommended — easier to reason)
{ type: "spring", duration: 0.5, bounce: 0.2 }

// Traditional physics
{ type: "spring", mass: 1, stiffness: 100, damping: 10 }
```

### When to Use What

| สถานการณ์ | เทคโนโลยี |
|-----------|-----------|
| Predetermined motion | CSS transitions / `@starting-style` |
| Dynamic, interruptible | CSS transitions / WAAPI |
| Gesture-driven | Springs (via `useSpring` / Motion) |
| Scroll-driven | `IntersectionObserver` + CSS |
| Marketing/delight | CSS keyframes |

## Performance Checklist

- [ ] Animate เฉพาะ `transform` + `opacity` (GPU composited)
- [ ] ไม่ animate `width`, `height`, `margin`, `padding`, `top`, `left`
- [ ] ใช้ CSS transitions แทน keyframes สำหรับ dynamic UI
- [ ] เปลี่ยน CSS variable บน parent → ใช้ transform โดยตรง
- [ ] ⚠️ Framer Motion `x`/`y`/`scale` shorthand **ไม่** hardware accelerated — ใช้ `transform` string แทนตอน load หนัก
- [ ] WAAPI > JS animation สำหรับ programmatic control

## Accessibility Checklist

- [ ] `@media (prefers-reduced-motion: reduce)` — keep opacity/color, remove movement
- [ ] `@media (hover: hover) and (pointer: fine)` — gate hover animations
- [ ] Tooltip delay เฉพาะครั้งแรก — ครั้งถัดไป instant
- [ ] ไม่มี animation บน keyboard actions

## แหล่งอ้างอิง

- **[emilkowalski/skills](https://github.com/emilkowalski/skills)** — ต้นฉบับของหลักการนี้
- **[animations.dev](https://animations.dev/)** — คอร์สโดย Emil Kowalski
- **[easing.dev](https://easing.dev/)** — สร้าง custom easing curves
- **[easings.co](https://easings.co/)** — predefined custom easings
- **[7 Practical Animation Tips](https://emilkowal.ski/ui/7-practical-animation-tips)** — โดย Emil
- **[Agents with Taste](https://emilkowal.ski/ui/agents-with-taste)** — ทำไม agents ถึงต้องการ design taste
