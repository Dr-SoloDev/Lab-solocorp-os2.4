#!/usr/bin/env python3
"""Read-only stdio MCP handshake, schema check, and missing-input check call."""
import argparse
import json
import os
import select
import shlex
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SKILL = Path("/home/drsolodev/.claude/skills/ffmpeg-skill")
SERVER = SKILL / "mcp/server.py"
PACKAGE = SKILL / "package.json"
DEFAULT_EVIDENCE = REPO / "bus/evidence/2026-10-26/ffmpeg-skill-mcp-builder-d2-authored.json"
REQUIRED = ["probe", "cut", "silence", "loudness", "fit", "caption", "look", "check", "render"]
PROTOCOL = "2024-11-05"


def encoded(message):
    return json.dumps(message, ensure_ascii=False, separators=(",", ":")) + "\n"


def receive(proc, expected_id):
    ready, _, _ = select.select([proc.stdout], [], [], 20)
    if not ready:
        raise TimeoutError(f"timed out waiting for MCP id {expected_id}")
    raw = proc.stdout.readline()
    if not raw:
        raise RuntimeError(f"server closed stdout before MCP id {expected_id}")
    reply = json.loads(raw)
    if reply.get("id") != expected_id:
        raise RuntimeError(f"unexpected MCP reply id: {reply.get('id')}")
    return raw, reply


def schema_ok(schema):
    return bool(isinstance(schema, dict) and schema.get("type") == "object"
                and isinstance(schema.get("properties"), dict)
                and isinstance(schema.get("required", []), list)
                and set(schema.get("required", [])).issubset(schema.get("properties", {})))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence", type=Path, default=DEFAULT_EVIDENCE)
    args = parser.parse_args()
    evidence = args.evidence if args.evidence.is_absolute() else REPO / args.evidence
    runner_command = ("source .venv/bin/activate && export PYTHONPATH=. && "
                      + shlex.join(["python", "axis_mcp/tools/ffmpeg_skill_d2_runner.py", *sys.argv[1:]]))
    report = {"record_type": "d2_read_only_mcp_runner", "runner_command": runner_command,
              "evidence_output_path": str(evidence), "server_command": [sys.executable, str(SERVER)],
              "mcp_requests": [], "mcp_replies": [], "raw_stdout": "", "raw_stderr": "",
              "validation": {"checks": {}}, "server_exit_code": None, "runner_exit_code": 1}
    if evidence.exists():
        raise FileExistsError(f"refusing to overwrite evidence: {evidence}")
    proc = None
    raw_lines = []
    try:
        if not SERVER.is_file() or not PACKAGE.is_file():
            raise FileNotFoundError(f"local ffmpeg-skill installation incomplete: {SKILL}")
        package = json.loads(PACKAGE.read_text(encoding="utf-8"))
        report["installed_package"] = {"name": package.get("name"), "version": package.get("version")}
        env = os.environ.copy()
        env["FFMPEG_SKILL_MCP_FULL"] = "0"
        proc = subprocess.Popen(report["server_command"], cwd=SKILL, env=env, text=True,
                                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1)
        init = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
            "protocolVersion": PROTOCOL, "capabilities": {},
            "clientInfo": {"name": "solocorp-ffmpeg-d2", "version": "1.0.0"}}}
        report["mcp_requests"].append(init)
        proc.stdin.write(encoded(init)); proc.stdin.flush()
        raw, init_reply = receive(proc, 1); raw_lines.append(raw); report["mcp_replies"].append(init_reply)
        notification = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        report["mcp_requests"].append(notification)
        proc.stdin.write(encoded(notification)); proc.stdin.flush()
        list_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        report["mcp_requests"].append(list_request)
        proc.stdin.write(encoded(list_request)); proc.stdin.flush()
        raw, list_reply = receive(proc, 2); raw_lines.append(raw); report["mcp_replies"].append(list_reply)
        tools = list_reply.get("result", {}).get("tools", [])
        by_name = {item.get("name"): item for item in tools}
        check_tool = by_name.get("check", {})
        schema = check_tool.get("inputSchema", {})
        input_required = any("input" in branch.get("required", []) for branch in schema.get("anyOf", []))
        check_schema_safe = (schema_ok(schema) and schema.get("properties", {}).get("input", {}).get("type") == "string"
                             and input_required and check_tool.get("annotations", {}).get("readOnlyHint") is True)
        if not check_schema_safe:
            raise RuntimeError("blocker: installed check schema lacks read-only required string input")
        with tempfile.TemporaryDirectory(prefix="solocorp-ffmpeg-d2-", dir="/tmp") as private_dir:
            fixture = Path(private_dir) / "input.mp4"
            absent_before = not fixture.exists()
            if not absent_before:
                raise RuntimeError(f"blocker: fixture unexpectedly exists: {fixture}")
            call = {"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                    "params": {"name": "check", "arguments": {"input": str(fixture), "no_loudness": True}}}
            report["mcp_requests"].append(call)
            proc.stdin.write(encoded(call)); proc.stdin.flush()
            raw, call_reply = receive(proc, 3); raw_lines.append(raw); report["mcp_replies"].append(call_reply)
            report["check_fixture"] = {"path": str(fixture), "private_temp_directory": private_dir,
                                           "absent_immediately_before_call": absent_before,
                                           "still_absent_after_call": not fixture.exists()}
            result = call_reply.get("result", {})
            structured = result.get("structuredContent", {})
            error = structured.get("error", {})
            expected = f"input not found: {fixture}"
            check_validation = {
                "check_schema_read_only_required_string_input": check_schema_safe,
                "fixture_absent_before_call": absent_before,
                "fixture_still_absent_after_call": not fixture.exists(),
                "tool_returned_is_error": result.get("isError") is True,
                "structured_status_failed": structured.get("status") == "failed",
                "error_kind_input": error.get("kind") == "input",
                "error_code_input_invalid": error.get("code") == "INPUT_INVALID",
                "exact_missing_input_message": error.get("message") == expected,
                "tool_exit_code_one": structured.get("exit_code") == 1,
            }
        proc.stdin.close()
        report["server_exit_code"] = proc.wait(timeout=20)
        report["raw_stderr"] = proc.stderr.read()
        report["raw_stdout"] = "".join(raw_lines)
        schemas = {name: schema_ok(by_name.get(name, {}).get("inputSchema")) for name in REQUIRED}
        checks = {"initialize_success": "result" in init_reply,
                  "protocol_version_matches": init_reply.get("result", {}).get("protocolVersion") == PROTOCOL,
                  "server_name_matches": init_reply.get("result", {}).get("serverInfo", {}).get("name") == "ffmpeg-skill",
                  "server_version_matches_package": init_reply.get("result", {}).get("serverInfo", {}).get("version") == package.get("version"),
                  "tools_list_success": "result" in list_reply, "required_tools_present": all(n in by_name for n in REQUIRED),
                  "required_schemas_valid": all(schemas.values()), "check_call_server_exit_zero": report["server_exit_code"] == 0}
        checks.update(check_validation)
        report["validation"] = {"checks": checks, "required_tool_schema_checks": schemas,
                                   "advertised_tool_count": len(tools), "check_tool_checks": check_validation}
        report["runner_exit_code"] = 0 if all(checks.values()) else 1
    except Exception as exc:
        report["error"] = f"{type(exc).__name__}: {exc}"
        if proc and proc.poll() is None:
            proc.terminate(); report["server_exit_code"] = proc.wait(timeout=5)
        report["raw_stdout"] = "".join(raw_lines)
        if proc and proc.stderr and proc.poll() is not None:
            report["raw_stderr"] = proc.stderr.read()
    rendered = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text(rendered, encoding="utf-8")
    sys.stdout.write(rendered)
    return report["runner_exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
