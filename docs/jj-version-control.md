# Jujutsu (jj) — Version Control แบบ Undo-First สำหรับ SoloCorp OS 2.4

> **"ลงทุนที่ระบบก่อน → ระบบชัดทุกอย่างราบรื่น"** — jj คือระบบ VCS ที่ออกแบบมาให้ย้อนกลับได้ทุกขั้นตอน

---

## 📌 jj คืออะไร

**Jujutsu** (jj) เป็นเครื่องมือ version control ยุคใหม่ที่รันบน Git repository เดิม 100% — ไม่ต้องย้าย repo, ไม่ต้องเปลี่ยน workflow, เบื้องหลังยังเป็น `.git` ปกติ

จุดขายหลัก: **ทำให้การย้อนกลับเป็นเรื่องปกติ** — ไม่ใช่แค่ฟีเจอร์ฉุกเฉินแบบ `git reflog`

| Pain Point | Git | jj |
|---|---|---|
| Staging Area | ต้อง `git add` → `git commit` | ❌ ไม่มี — auto-snapshot ทันทีที่แก้ไฟล์ |
| Undo | `git reflog` แล้วเดา hash เอา | `jj undo` — ย้อน operation ไหนก็ได้ |
| Conflict | rebase ค้างกลางทาง | เก็บ conflict ใน commit แก้ทีหลัง |
| Stash | `git stash` pop แล้วงง | ❌ ไม่ต้อง stash — commit เลย |
| Operation Log | `git reflog` (อ่านยาก) | `jj op log` — จดทุกคำสั่ง เป็น chain ชัดเจน |

---

## 🚀 ติดตั้ง (Linux x86_64)

```bash
# ดาวน์โหลด binary ล่าสุดจาก GitHub Release
curl -sL "https://api.github.com/repos/jj-vcs/jj/releases/latest" | \
  grep "browser_download_url.*linux.*x86_64.*musl" | cut -d '"' -f 4 | \
  xargs curl -sL -o /tmp/jj.tar.gz
tar xzf /tmp/jj.tar.gz -C /tmp
cp /tmp/jj-*/jj ~/.local/bin/jj
jj --version
```

---

## ⚡ เริ่มใช้ใน SoloCorp OS 2.4

```bash
cd ~/projects/Lab-solocorp-os2.4

# 1. Init jj บน git repo เดิม (ครั้งเดียว)
jj git init

# 2. Track remote branch
jj bookmark track main --remote=origin

# 3. ตั้งชื่อ + email (ครั้งเดียว — global config)
jj config set --user user.name "Dr.solodev"
jj config set --user user.email "drsolodev@gmail.com"

# 4. เริ่มทำงาน
# แก้ไฟล์... → jj auto-snapshot ให้ → แค่ describe
jj describe -m "feat: your commit message"
```

---

## 🔄 Workflow ประจำวัน (SoloCorp OS)

```bash
# ── เริ่มวัน ──
jj git fetch
jj bookmark move main --from main@origin

# ── ทำงาน ──
vim central_bus/config.yaml
vim bus/routing.yaml

# jj auto-snapshot ให้แล้วทุกครั้งที่เซฟไฟล์!

# ── Commit ──
jj describe -m "feat: add new agent routing rule"

# ── แก้ message ผิด? ──
jj undo        # ← กลับก่อน describe
jj describe -m "feat: add new agent routing rule for content-creator"

# ── Push ──
jj bookmark move main --to @
jj git push
```

---

## 📖 คำสั่งเทียบ Git ↔ jj

| jj | Git | หมายเหตุ |
|----|-----|----------|
| `jj log` | `git log --oneline --graph` | แสดง graph + change ID |
| `jj show` | `git show` | ดู diff |
| `jj describe -m "msg"` | `git add -A && git commit -m "msg"` | ไม่ต้อง add |
| `jj undo` | — | ย้อน operation ล่าสุด |
| `jj op log` | `git reflog` | ประวัติทุก operation |
| `jj bookmark move main --to @` | `git branch -f main` | ย้าย branch |
| `jj bookmark track main --remote=origin` | `git branch -u origin/main` | sync remote |
| `jj git push` | `git push` | push ขึ้น GitHub |
| `jj git fetch` | `git fetch` | ดึงจาก remote |
| `jj new` | `git checkout -b` | สร้าง changeset ใหม่ |
| `jj abandon` | `git branch -D` | ทิ้ง changeset |
| `jj squash` | `git rebase -i` (squash) | รวม commits |
| `jj metaedit --update-author` | `git commit --amend --reset-author` | แก้ author |

---

## 🧪 ผลทดสอบจริง — 1 ก.ค. 2026

### ทดสอบบน `bangkok-pos`

| ฟีเจอร์ | ผล |
|---------|-----|
| Auto-snapshot | ✅ ไฟล์ `auth/config.ts` ที่ค้างอยู่ ถูก auto-commit ทันที |
| jj undo | ✅ `jj describe` → `jj undo` → กลับเป็น `(no description)` ใน 0.05 วิ |
| Operation Log | ✅ เห็น chain: init → snapshot → describe → undo ครบ |
| Git Interop | ✅ `git log` ยังเห็น history ปกติ ใช้คู่กันได้ |
| Push | ✅ `jj bookmark move main --to @` → `jj git push` → ขึ้น GitHub |
| Remote | ✅ `jj bookmark track main --remote=origin` → sync |

### jj op log ตัวอย่าง

```
@  undo: restore to operation d81fb89789cf   ← jj undo
○  describe commit 31d5e8e4                   ← jj describe -m "..."
○  snapshot working copy                      ← auto-snapshot อัตโนมัติ
○  import git head                            ← jj git init
```

---

## ⚠️ ข้อควรระวัง

| เรื่อง | รายละเอียด |
|--------|-----------|
| **Pre-1.0** | jj ยังอยู่ v0.42.0 — รูปแบบไฟล์ `.jj/` อาจเปลี่ยนก่อน 1.0 |
| **ความเร็ว** | ไม่ได้เร็วกว่า git — จุดขายคือ **safety + simplicity** |
| **ใช้ร่วมกับ git** | ใช้ `jj` กับ `git` ใน repo เดียวกันได้ — git ไม่รู้เรื่อง jj changeset |
| **ทีม** | ใช้คนเดียวก่อนได้ — ไม่ต้องให้ทั้งทีมย้ายมาพร้อมกัน |

---

## 🔗 SoloCorp OS 2.4 — Adoption Strategy

```
Phase 1 (ปัจจุบัน): เริ่มใช้ jj ใน Lab-solocorp-os2.4 + bangkok-pos
Phase 2: สร้าง skill jj-workflow สำหรับ agent profiles
Phase 3: ทั้งองค์กรใช้ jj เป็น VCS หลัก
```

### Projects ที่ใช้ jj แล้ว

| โปรเจกต์ | Repo | Status |
|----------|------|--------|
| Bangkok POS | `Dr-SoloDev/bangkok-pos` | ✅ Active |
| SoloCorp OS 2.4 | `Dr-SoloDev/Lab-solocorp-os2.4` | ✅ Active |

---

## 📚 อ้างอิง

- [jj-vcs.github.io](https://jj-vcs.github.io/jj/) — Official docs
- [GitHub: jj-vcs/jj](https://github.com/jj-vcs/jj) — Source (Rust, Apache 2.0)
- [GitHub: faldor20/jj_tui](https://github.com/faldor20/jj_tui) — TUI interface
- ผู้สร้าง: **Martin von Zweigbergk** (@Google — ไม่ใช่ผลิตภัณฑ์ทางการของ Google)
- คอมมิวนิตี้: Lobsters, Hacker News, `/r/jj_vcs`
