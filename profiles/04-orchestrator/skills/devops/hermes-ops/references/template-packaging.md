# Template Packaging — F5 Experiment Session Log

**Date:** 18 มิ.ย. 2026
**Context:** SoloCorp OS 2.0 Lab — F5 Template Packaging experiment หลังวิเคราะห์ agencycli + Nasiko + agent-skills + WoJiSama

## Goal

สร้างระบบ portable backup/restore สำหรับ Hermes profiles, config, skills — pack เป็น .tar.gz พร้อม checksum manifest สามารถส่งไปเครื่องอื่นหรือ restore กลับได้

## Files Created

| File | Path | Purpose |
|------|------|---------|
| `solo-corp-pack.sh` | `.../f5-template-packaging/` | Pack script (~280 lines) |
| `solo-corp-unpack.sh` | `.../f5-template-packaging/` | Unpack/verify script (~200 lines) |
| `solo-corp-manifest.yaml` | `.../f5-template-packaging/` | Manifest template |
| `solo-corp-default-excludes.txt` | `.../f5-template-packaging/` | Default exclude patterns |
| `test-fixtures/` | `.../f5-template-packaging/` | 6 profiles + config + skills |
| `output/solo-corp-test.tar.gz` | `.../f5-template-packaging/` | Test output |
| `output/solo-corp-test.tar.gz.sha256` | `.../f5-template-packaging/` | Test checksum |

## Architecture

```
solo-corp-pack.sh                        solo-corp-unpack.sh
     │                                         │
     ▼                                         ▼
SOURCE_DIR ──── tar + gzip ────► .tar.gz ◄──── verify sha256 ────► TARGET_DIR
     │              │                │                                 │
     │              │           solo-corp-                         manifest
     │              │           manifest.yaml                       excluded
     │              ▼                │
     └────── .sha256 ────────────────┘
```

### Key Design Decision

`tar -rf` cannot append to `.tar.gz` (compressed archives don't support append). Solution: two-step process:
1. Create uncompressed `.tar` from source files
2. `tar -rf` append `solo-corp-manifest.yaml` to the uncompressed tar
3. `gzip` the combined tar → final `.tar.gz`
4. Delete intermediate `.tar`

## Test Results (7/7 Passed)

| # | Test | Command | Result |
|:-:|------|---------|:------:|
| 1 | Version | `--version` | ✅ v0.1.0 |
| 2 | Help | `--help` | ✅ |
| 3 | Dry-run pack | `--dry-run ./test-fixtures` | ✅ แสดง 7 directories + manifest |
| 4 | Actual pack | `./test-fixtures -o output/test.tar.gz` | ✅ 23 items, 8.0K, SHA256 generated |
| 5 | Verify-only | `--verify-only output/test.tar.gz` | ✅ integrity pass |
| 6 | Dry-run unpack | `--dry-run -t /tmp/restore` | ✅ แสดง 12 directories (🆕 new) |
| 7 | Actual restore | `-t /tmp/solo-corp-test-restore` | ✅ 10 files restored, manifest excluded |

## Test Fixtures

```bash
~/projects/solocorp-os/lab/experiments/f5-template-packaging/test-fixtures/
├── config.yaml              # Copied from ~/.hermes/config.yaml (610 lines)
├── profiles/                # 6 profiles from ~/.hermes/profiles/
│   ├── architect/config.yaml
│   ├── ceo/config.yaml
│   ├── cfo/config.yaml
│   ├── legal/config.yaml
│   ├── mkt/config.yaml
│   └── orchestrator/config.yaml
├── skills/                  # Empty dir (structure preserved)
├── context/.gitkeep         # Optional (SoloCorp layer)
├── goals/.gitkeep           # Optional
├── cron/.gitkeep            # Optional
└── inbox/                   # Empty dir (structure preserved)
```

## Known Bugs (Fixed During Development)

### Bug 1: Manifest path in tar command
**Symptom:** `tar: solo-corp-manifest.yaml: Cannot stat: No such file or directory`
**Root cause:** Manifest was added to `PACK_DIRS` array (referenced from `$SOURCE_DIR`) but the file lived in `$TEMP_PACK_DIR`. Tar couldn't find it.
**Fix:** Changed to two-step: create uncompressed tar from source, then `tar -rf` append manifest from temp dir, then gzip.
**File:** `solo-corp-pack.sh` lines 217-236

## Usage Patterns

### Pattern 1: Daily backup to ~/backups/
```bash
./solo-corp-pack.sh ~/.hermes -o ~/backups/hermes-$(date +%Y%m%d).tar.gz
```

### Pattern 2: Machine-to-machine migration
```bash
# Machine A — pack
./solo-corp-pack.sh ~/.hermes -o solocorp.tar.gz
scp solocorp.tar.gz solocorp.tar.gz.sha256 machine-b:~

# Machine B — verify + restore
./solo-corp-unpack.sh --verify-only ~/solocorp.tar.gz
./solo-corp-unpack.sh ~/solocorp.tar.gz -t ~/.hermes
```

### Pattern 3: Pre-reorg safety snapshot
```bash
# Before any skill/profile reorganization
./solo-corp-pack.sh ~/.hermes -o ~/backups/pre-reorg-$(date +%Y%m%d).tar.gz
# If something breaks:
./solo-corp-unpack.sh ~/backups/pre-reorg-$(date +%Y%m%d).tar.gz -t ~/.hermes -f
```

## Related Files

- `~/projects/solocorp-os/lab/experiments/f5-template-packaging/README.md` — Full experiment docs + checklist
- `~/projects/solocorp-os/lab/docs/architecture.md` — SoloCorp Layer Architecture
- `devops/hermes-ops/SKILL.md` — Part G: Profile/Skill Backup & Portability
