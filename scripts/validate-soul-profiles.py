#!/usr/bin/env python3
"""
WP2: Quality Gate Validation — 7-Criteria SOUL.md Profile Checker
Owner: @architect-songsak (พี่ทรงศักดิ์)
"""

import os
import re
import sys
from pathlib import Path

PROFILES_DIR = Path(__file__).resolve().parent.parent / "profiles"
PASS_THRESHOLD = 5


def find_profiles():
    souls = sorted(PROFILES_DIR.glob("*/SOUL.md"))
    if not souls:
        print("❌ No SOUL.md files found under profiles/")
        sys.exit(1)
    return souls


def get_profile_slug(path):
    return str(path.relative_to(PROFILES_DIR.parent))


def count_situation_rules(text):
    lines = text.split("\n")
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        has_arrow = any(c in stripped for c in ("—", "–", "→", "=>"))
        has_conditional = any(w in stripped for w in ("ต้อง", "เมื่อ", "ถ้า", "if ", "when ", "after ", "while "))
        has_prohibition = any(w in stripped for w in ("ห้าม", "don't", "never", "avoid", "อย่า"))
        if stripped.startswith(("- ", "* ", "1.", "2.", "3.", "4.", "5.", "6.", "7.", "8.", "9.", "0.")):
            if (has_arrow or has_conditional or has_prohibition) and len(stripped) > 20:
                count += 1
    return count


def count_examples(text):
    lines = text.split("\n")
    count = 0
    in_example_block = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^-\s*\*\*", stripped) and ":" in stripped:
            count += 1
        elif stripped.startswith("- ") and '"' in stripped and len(stripped) > 40:
            count += 1
        elif re.match(r"^```", stripped):
            in_example_block = not in_example_block
    # Count markdown code-snippet examples
    snippet_count = len(re.findall(r"```", text)) // 2
    return max(count, snippet_count)


def count_catchphrases(text):
    quotes = re.findall(r'"([^"]{8,})"', text)
    unique = set(q.strip() for q in quotes)
    return len(unique)


def has_priority_ranking(text):
    patterns = [
        r"(?i)priority\s*[:\-]?\s*[Pp]\d",
        r"(?i)ranked?\s*(list|priority|order)",
        r"(?i)ลำดับความสำคัญ",
        r"(?i)priority\s*>",
        r"(?i)[Pp]\d\s*[>→]",
        r"(?i)correctness\s*>\s*speed",
        r"(?i)speed\s*>\s*quality",
    ]
    for pat in patterns:
        if re.search(pat, text):
            return True
    # Check for numbered lists that look like priorities (e.g. "1. ... 2. ... 3. ...")
    lines = text.split("\n")
    priority_lines = 0
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+\.", stripped) and len(stripped) > 15:
            priority_lines += 1
    return priority_lines >= 3


def has_scope_defined(text):
    patterns = [
        r"(?i)(own|responsible|รับผิดชอบ|เจ้าของ|managed? by|reports to|สังกัด|แผนก)",
        r"(?i)(system|domain|pipeline|module|service|platform|interface|component)",
        r"(?i)(ออกแบบ|ดูแล|จัดการ|ควบคุม|design|manage|architect|handle|operate)",
    ]
    score = 0
    for pat in patterns:
        if re.search(pat, text):
            score += 1
    return score >= 2


def scan_generic_filler(text):
    filler_phrases = [
        "they tend to", "generally speaking",
        "in most cases", "typically",
        "มักจะ", "โดยทั่วไป",
        "usually", "as a rule of thumb (when overused)",
    ]
    findings = []
    for phrase in filler_phrases:
        matches = [(m.start(), phrase) for m in re.finditer(re.escape(phrase), text, re.IGNORECASE)]
        findings.extend(matches)
    return findings


def check_tag_rule_translation(text):
    tag_sections = ["🎭 Identity", "🧠 ข้อมูลประจำตัว", "Core Personality", "Tags", "traits", "personality"]
    has_tags = False
    for tag in tag_sections:
        if tag in text:
            has_tags = True
            break
    if not has_tags:
        return False, "No personality tag section found"

    # Check that tags are followed by behavioral rules (section with "กฎ" or "rules")
    has_rules_section = bool(re.search(r"(?i)(กฎ|rules?|ต้องปฏิบัติ|สำคัญ)", text))
    if not has_rules_section:
        return False, "Tags found but no behavioral rules section"

    # Count behavioral rules
    rules_count = 0
    lines = text.split("\n")
    for line in lines:
        stripped = line.strip()
        if re.match(r"^\d+[.)]\s", stripped) and len(stripped) > 20:
            rules_count += 1
    if rules_count < 3:
        return False, f"Only {rules_count} behavioral rules found (need ≥3)"

    return True, f"Found {rules_count} behavioral rules linked to identity"


def validate_single(path):
    slug = get_profile_slug(path)
    text = path.read_text(encoding="utf-8")

    results = {}
    score = 0
    total = 7

    # 1. Concreteness
    rule_count = count_situation_rules(text)
    if rule_count >= 5:
        results["Concreteness"] = (True, f"found {rule_count} situation→behavior rules")
        score += 1
    else:
        results["Concreteness"] = (False, f"only {rule_count} situation→behavior rules, need ≥5")

    # 2. Examples count
    ex_count = count_examples(text)
    if ex_count >= 3:
        results["Examples"] = (True, f"found {ex_count} dialogue/response examples")
        score += 1
    else:
        results["Examples"] = (False, f"only {ex_count} dialogue example{'s' if ex_count != 1 else ''}, need ≥3")

    # 3. Catchphrase density
    cp_count = count_catchphrases(text)
    if ">" in text and cp_count > 0:
        # Block quotes (>) often contain catchphrases
        block_quotes = re.findall(r'>\s*"([^"]+)"', text)
        cp_count = max(cp_count, len(block_quotes))
    if cp_count >= 2:
        results["Catchphrases"] = (True, f"found {cp_count} catchphrases")
        score += 1
    else:
        results["Catchphrases"] = (False, f"only {cp_count} catchphrase{'s' if cp_count != 1 else ''}, need ≥2")

    # 4. Priority ranking
    if has_priority_ranking(text):
        results["Priority Ranking"] = (True, "explicit priority list found")
        score += 1
    else:
        results["Priority Ranking"] = (False, "no explicit priority ranking found (e.g. P0>P1 or ranked list)")

    # 5. Scope defined
    if has_scope_defined(text):
        results["Scope Defined"] = (True, "systems/domains owned are listed")
        score += 1
    else:
        results["Scope Defined"] = (False, "no clear system/domain ownership stated")

    # 6. No generic filler
    fillers = scan_generic_filler(text)
    if not fillers:
        results["No Generic Filler"] = (True, "no generic filler phrases detected")
        score += 1
    else:
        phrases_used = set(f[1] for f in fillers)
        results["No Generic Filler"] = (
            False,
            f"found generic filler: {', '.join(sorted(phrases_used))}"
        )

    # 7. Tag→Rule translation
    tag_ok, tag_msg = check_tag_rule_translation(text)
    if tag_ok:
        results["Tag→Rule Translation"] = (True, tag_msg)
        score += 1
    else:
        results["Tag→Rule Translation"] = (False, tag_msg)

    return slug, results, score, total


def print_report(slug, results, score, total):
    print(f"{slug}:")
    for criterion, (passed, detail) in results.items():
        icon = "✅" if passed else "❌"
        print(f"  {icon} {criterion} — {detail}")
    status = "✅ PASS" if score >= PASS_THRESHOLD else "❌ FAIL"
    print(f"  Score: {score}/{total} — {status}")
    if score < PASS_THRESHOLD:
        missing = [k for k, (p, _) in results.items() if not p]
        print(f"  Needs work on: {', '.join(missing)}")
    print()


def main():
    profiles = find_profiles()
    print(f"🔍 Validating {len(profiles)} profiles against 7 Quality Gate criteria\n")

    all_passed = True
    for path in profiles:
        slug, results, score, total = validate_single(path)
        print_report(slug, results, score, total)
        if score < PASS_THRESHOLD:
            all_passed = False

    passed_count = sum(1 for p in profiles if validate_single(p)[2] >= PASS_THRESHOLD)

    print("=" * 50)
    print(f"Results: {passed_count}/{len(profiles)} profiles passed (threshold: {PASS_THRESHOLD}/7)")
    if all_passed:
        print("✅ All profiles pass quality gate")
        return 0
    else:
        print("❌ Some profiles need improvement before CI can pass")
        return 1


if __name__ == "__main__":
    sys.exit(main())
