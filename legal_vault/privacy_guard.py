#!/usr/bin/env python3
"""
Privacy Guard — PII Scanner & Auto-Redactor

Part of Legal Vault (SoloCorp OS — WP6)
Scans files for personally identifiable information (PII) and sensitive data.

Usage:
    python3 legal_vault/privacy_guard.py file.txt
    python3 legal_vault/privacy_guard.py path/to/dir/
    python3 legal_vault/privacy_guard.py file.txt --redact
    python3 legal_vault/privacy_guard.py file.txt --verbose
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import NamedTuple


class Finding(NamedTuple):
    line: int
    category: str
    matched: str


PATTERNS: list[tuple[re.Pattern, str, str]] = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b'), "email", "[REDACTED]"),
    (re.compile(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3}[-.\s]?\d{3,4}\b'), "phone", "[REDACTED]"),
    (re.compile(r'\b(?:sk-|pk-|xoxb-|xoxp-|ghp_|gho_|glpat-|ghu_|ghs_)[A-Za-z0-9_-]{20,}\b'), "api_key", "[REDACTED]"),
    (re.compile(r'\b(?:AKIA|ASIA)[A-Z0-9]{16}\b'), "api_key", "[REDACTED]"),
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), "ssn", "[REDACTED]"),
    (re.compile(r'\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b'), "ip_address", "[REDACTED]"),
]

SCANNABLE_EXTENSIONS: set[str] = {".md", ".txt", ".json", ".py", ".yml", ".yaml", ".csv", ".html", ".xml", ".toml", ".cfg", ".ini", ".env", ".sh", ".bat"}
EXCLUDE_DIRS: set[str] = {".git", "__pycache__", "node_modules", ".venv", "versions"}


def scan_file(file_path: Path, verbose: bool = False) -> list[Finding]:
    findings: list[Finding] = []
    try:
        content = file_path.read_text(encoding="utf-8", errors="replace")
    except Exception as exc:
        if verbose:
            print(f"  ⚠  Skipping {file_path.name}: {exc}")
        return findings

    for line_num, line in enumerate(content.splitlines(), 1):
        for pattern, category, _ in PATTERNS:
            for match in pattern.finditer(line):
                raw = match.group()
                if category == "ip_address" and raw in ("127.0.0.1", "0.0.0.0", "255.255.255.255"):
                    continue
                if category == "phone":
                    digits = re.sub(r"[^\d]", "", raw)
                    if len(digits) < 7:
                        continue
                findings.append(Finding(line=line_num, category=category, matched=raw))

    return findings


def scan_path(target: Path, verbose: bool = False) -> dict[Path, list[Finding]]:
    results: dict[Path, list[Finding]] = {}
    if target.is_file():
        findings = scan_file(target, verbose=verbose)
        if findings:
            results[target] = findings
        return results

    for file_path in sorted(target.rglob("*")):
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in SCANNABLE_EXTENSIONS:
            continue
        parts = file_path.relative_to(target).parts
        if any(part in EXCLUDE_DIRS for part in parts):
            continue
        findings = scan_file(file_path, verbose=verbose)
        if findings:
            results[file_path] = findings
    return results


def redact_file(file_path: Path) -> int:
    content = file_path.read_text(encoding="utf-8", errors="replace")
    count = 0
    for pattern, _, replacement in PATTERNS:
        content, n = pattern.subn(replacement, content)
        count += n
    if count:
        file_path.write_text(content, encoding="utf-8")
    return count


def format_matched(category: str, raw: str) -> str:
    if category == "api_key":
        if len(raw) > 10:
            return raw[:3] + "..." + raw[-4:]
        return raw[:3] + "..."
    return raw


def main() -> None:
    parser = argparse.ArgumentParser(description="Privacy Guard — PII Scanner & Auto-Redactor")
    parser.add_argument("target", help="File or directory to scan")
    parser.add_argument("--redact", action="store_true", help="Replace PII with [REDACTED] in-place")
    parser.add_argument("--verbose", action="store_true", help="Show skipped files")
    args = parser.parse_args()

    target_path = Path(args.target)
    if not target_path.exists():
        print(f"Error: path not found — {target_path}")
        sys.exit(1)

    results = scan_path(target_path, verbose=args.verbose)

    total = 0
    for file_path, findings in results.items():
        print(f"Scanning: {file_path}")
        for f in findings:
            masked = format_matched(f.category, f.matched)
            print(f"  ⚠️ {f.category}: {masked} (line {f.line})")
        total += len(findings)

    if total == 0:
        print("✅ No PII detected.")
        return

    print(f"Found: {total} PII items — run with --redact to sanitize")

    if args.redact:
        redacted_total = 0
        for file_path in results:
            count = redact_file(file_path)
            if count:
                print(f"  ✏️  Redacted {count} item(s) in {file_path}")
                redacted_total += count
        print(f"✅ Redacted {redacted_total} item(s) total.")


if __name__ == "__main__":
    main()
