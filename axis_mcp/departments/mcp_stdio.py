"""Small newline-JSON-RPC client for local stdio MCP engines."""

from __future__ import annotations

import json
import os
import queue
import subprocess
import threading
import time
from pathlib import Path
from typing import Any


class MCPStdioError(RuntimeError):
    """An MCP process or request failed."""


class MCPStdioClient:
    def __init__(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        env: dict[str, str] | None = None,
        unset_env: tuple[str, ...] = (),
        startup_timeout: float = 15,
    ) -> None:
        if not command or any(
            not isinstance(part, str) or not part for part in command
        ):
            raise MCPStdioError("MCP command must be a non-empty string list")
        process_env = os.environ.copy()
        for key in unset_env:
            process_env.pop(key, None)
        if env:
            process_env.update(env)
        self._process = subprocess.Popen(
            command,
            cwd=str(cwd) if cwd else None,
            env=process_env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            bufsize=1,
        )
        self._messages: queue.Queue[str | None] = queue.Queue()
        self._reader = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader.start()
        self._request_id = 0
        try:
            self.request(
                "initialize",
                {
                    "protocolVersion": "2025-11-25",
                    "capabilities": {},
                    "clientInfo": {"name": "solocorp-media-hub", "version": "1.0"},
                },
                timeout=startup_timeout,
            )
            self._notify("notifications/initialized")
        except Exception:
            self.close()
            raise

    def _read_stdout(self) -> None:
        assert self._process.stdout is not None
        for line in self._process.stdout:
            self._messages.put(line)
        self._messages.put(None)

    def _notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        if self._process.stdin is None:
            raise MCPStdioError("MCP server stdin is unavailable")
        payload: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            payload["params"] = params
        try:
            self._process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPStdioError("MCP server closed its input stream") from exc

    def request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
        *,
        timeout: float = 30,
    ) -> dict[str, Any]:
        if self._process.stdin is None:
            raise MCPStdioError("MCP server stdin is unavailable")
        self._request_id += 1
        request_id = self._request_id
        payload: dict[str, Any] = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {},
        }
        try:
            self._process.stdin.write(json.dumps(payload, ensure_ascii=False) + "\n")
            self._process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPStdioError("MCP server closed its input stream") from exc

        deadline = time.monotonic() + timeout
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPStdioError(f"MCP request timed out: {method}")
            try:
                line = self._messages.get(timeout=remaining)
            except queue.Empty as exc:
                raise MCPStdioError(f"MCP request timed out: {method}") from exc
            if line is None:
                raise MCPStdioError("MCP server exited before responding")
            try:
                message = json.loads(line)
            except json.JSONDecodeError as exc:
                raise MCPStdioError("MCP server returned malformed JSON-RPC") from exc
            if message.get("id") != request_id:
                continue
            if "error" in message:
                error = message["error"]
                raise MCPStdioError(str(error.get("message", error))[:1200])
            result = message.get("result")
            if not isinstance(result, dict):
                raise MCPStdioError("MCP server returned a non-object result")
            return result

    def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
        *,
        timeout: float = 60,
    ) -> Any:
        result = self.request(
            "tools/call",
            {"name": name, "arguments": arguments or {}},
            timeout=timeout,
        )
        if result.get("isError"):
            detail = " ".join(
                str(item.get("text", ""))
                for item in result.get("content", [])
                if isinstance(item, dict)
            )
            raise MCPStdioError(detail[:1200] or f"MCP tool failed: {name}")
        structured = result.get("structuredContent")
        if isinstance(structured, dict):
            return structured
        text_blocks = [
            item.get("text", "")
            for item in result.get("content", [])
            if isinstance(item, dict) and item.get("type") == "text"
        ]
        if not text_blocks:
            return result.get("content", [])
        text = "\n".join(map(str, text_blocks)).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def close(self) -> None:
        if self._process.stdin is not None and not self._process.stdin.closed:
            try:
                self._process.stdin.close()
            except OSError:
                pass
        try:
            self._process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=5)

    def __enter__(self) -> "MCPStdioClient":
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
