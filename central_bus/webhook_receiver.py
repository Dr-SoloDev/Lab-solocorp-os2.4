"""
Webhook Receiver — Ingress Gateway for GitHub → Central Bus
พี่วุฒิ (Architect) · Step 1 of Event-Driven Architecture

Dual-mode operation:
  MODE 1 (Real-time): GitHub webhook POST → this receiver → Central Bus
  MODE 2 (Near-real-time): Cron polls gh CLI every N minutes → Central Bus
"""

import json
import hashlib
import hmac
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import BusMessage, Department, Priority
from .queue import enqueue
from .router import route, priority_for

# Configuration
WEBHOOK_SECRET_ENV = "GITHUB_WEBHOOK_SECRET"
POLL_INTERVAL_MINUTES = 1  # Near-real-time polling when webhook not available

# Repos to monitor (owner/repo)
WATCHED_REPOS = [
    "Dr-SoloDev/Lab-solocorp-os2.4",
    "Dr-SoloDev/scrap-pos",
]


def verify_signature(payload_body: bytes, signature_header: str, secret: str) -> bool:
    """Verify GitHub webhook HMAC-SHA256 signature."""
    if not secret or not signature_header:
        return False
    expected = "sha256=" + hmac.new(
        secret.encode(), payload_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)


def parse_github_event(event_type: str, payload: dict) -> Optional[BusMessage]:
    """Parse a GitHub webhook event into a BusMessage.

    Maps push events → Engineering (dev code committed)
    Maps PR events   → QA / Product (review needed)
    """
    repo_name = payload.get("repository", {}).get("full_name", "unknown")

    if event_type == "push":
        ref = payload.get("ref", "")
        branch = ref.replace("refs/heads/", "")
        commits = payload.get("commits", [])
        author = commits[0]["author"]["name"] if commits else "unknown"
        message = commits[0]["message"].split("\n")[0] if commits else "no message"

        # Determine project from branch name or repo
        project_id = repo_name.split("/")[-1]

        # Engineering commit → route to QA for testing
        if any(kw in message.lower() for kw in ["feat", "fix", "refactor", "build", "ci"]):
            return BusMessage(
                from_dept="engineering",
                to_dept="qa",
                type="HANDOFF",
                project_id=project_id,
                phase="dev",
                payload={
                    "text": f"[{branch}] {message} — by {author}",
                    "branch": branch,
                    "commits": [{"message": c["message"], "author": c["author"]["name"]} for c in commits],
                    "repo": repo_name,
                    "event": "push",
                },
                trace_id=f"gh-push-{payload.get('after', '')[:8]}",
                priority="high",
            )

    elif event_type == "pull_request":
        action = payload.get("action", "")
        pr = payload.get("pull_request", {})
        title = pr.get("title", "")
        body = pr.get("body", "")
        pr_number = pr.get("number", 0)
        branch = pr.get("head", {}).get("ref", "")

        project_id = repo_name.split("/")[-1]

        if action == "opened":
            # New PR → Product + QA notified
            return BusMessage(
                from_dept="engineering",
                to_dept="product",
                type="HANDOFF",
                project_id=project_id,
                phase="dev",
                payload={
                    "text": f"PR #{pr_number}: {title}",
                    "pr_number": pr_number,
                    "branch": branch,
                    "repo": repo_name,
                    "event": "pull_request",
                },
                trace_id=f"gh-pr-{pr_number}",
                priority="high",
            )

        elif action == "closed" and pr.get("merged"):
            # Merged PR → QA gate triggers auto-deploy
            return BusMessage(
                from_dept="engineering",
                to_dept="qa",
                type="HANDOFF",
                project_id=project_id,
                phase="qa",
                payload={
                    "text": f"PR #{pr_number} MERGED: {title}",
                    "pr_number": pr_number,
                    "branch": branch,
                    "repo": repo_name,
                    "event": "pull_request_merged",
                },
                trace_id=f"gh-pr-merge-{pr_number}",
                priority="critical" if "hotfix" in branch.lower() else "high",
            )

    return None


def receive_webhook(event_type: str, payload: dict, signature: str = "", secret: str = "") -> list[BusMessage]:
    """Process incoming GitHub webhook. Returns list of routed messages."""
    # Verify signature if secret is provided
    if secret and signature:
        raw = json.dumps(payload).encode()
        if not verify_signature(raw, signature, secret):
            return []

    msg = parse_github_event(event_type, payload)
    if msg is None:
        return []

    # Route to destination department
    msg.to_dept = route(msg)
    msg.priority = priority_for(msg.to_dept)

    # Enqueue in Central Bus
    enqueue(msg)

    return [msg]


def poll_recent_commits(repo: str, since_minutes: int = POLL_INTERVAL_MINUTES) -> list[BusMessage]:
    """Poll GitHub for recent commits — near-real-time Mode 2.
    Uses gh CLI to fetch recent commits. No webhook required.
    """
    try:
        result = subprocess.run(
            [
                "gh", "api",
                f"repos/{repo}/commits",
                "-q", ".[0:3]",
                "--jq", ".[].sha[:8]",
            ],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode != 0:
            return []

        shas = [s.strip() for s in result.stdout.strip().split("\n") if s.strip()]
        if not shas:
            return []

        # Get details for each commit
        messages = []
        for sha in shas:
            detail = subprocess.run(
                ["gh", "api", f"repos/{repo}/commits/{sha}",
                 "--jq", '{message: .commit.message, author: .commit.author.name, branch: .ref, sha: .sha}'],
                capture_output=True, text=True, timeout=10
            )
            if detail.returncode == 0:
                data = json.loads(detail.stdout)
                messages.append(
                    BusMessage(
                        from_dept="engineering",
                        to_dept="qa",
                        type="HANDOFF",
                        project_id=repo.split("/")[-1],
                        phase="dev",
                        payload={
                            "text": f"{data['message'].split(chr(10))[0]} — {data['author']}",
                            "sha": data["sha"][:8],
                            "repo": repo,
                            "event": "commit_polled",
                        },
                        trace_id=f"poll-{data['sha'][:8]}",
                        priority="high",
                    )
                )

        for msg in messages:
            msg.to_dept = route(msg)
            msg.priority = priority_for(msg.to_dept)
            enqueue(msg)

        return messages

    except Exception:
        return []


def poll_all_watched() -> dict[str, list[BusMessage]]:
    """Poll all watched repos. Returns {repo: [messages]}."""
    results = {}
    for repo in WATCHED_REPOS:
        msgs = poll_recent_commits(repo)
        if msgs:
            results[repo] = msgs
    return results
