"""
AO CLI Client — shell wrapper สำหรับ Agent Orchestrator

มี 2 คลาสหลัก:
  - ``AOResult``: Structured result container ใช้โดย adapter.py
  - ``AOClient``: primary class ใช้โดย adapter.py ใน ``AgentAdapter.invoke()``
  - ``AOCliClient``: legacy alias (AOClient subclass) สำหรับ backward compat

Architecture:
    adapter.py ใช้ ``AOClient.invoke()`` → calls subprocess → returns ``AOResult``
    bridge_integration.py ใช้ ``AOCliClient.run_agent()`` → calls subprocess → returns dict

Usage:
    from govctl_cli.ao.client import AOClient
    client = AOClient(cli_path="agent_orchestrator")
    result = client.run_agent("architect", "Design auth system")
    print(result["output"])
"""

import os
import sys
import time
import json
import signal
import logging
import subprocess
import shutil
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, NamedTuple, Optional

# ---------------------------------------------------------------------------
# Logging — เขียนไปที่ ~/.govctl/ao.log
# ---------------------------------------------------------------------------

AO_LOG_DIR = Path.home() / ".govctl"
AO_LOG_FILE = AO_LOG_DIR / "ao.log"

AO_LOG_DIR.mkdir(parents=True, exist_ok=True)

_log_handler = logging.FileHandler(AO_LOG_FILE)
_log_handler.setFormatter(logging.Formatter(
    "%(asctime)s [%(levelname)s] AO: %(message)s",
))
_log_handler.setLevel(logging.DEBUG)

log = logging.getLogger("govctl-ao")
log.setLevel(logging.DEBUG)
log.addHandler(_log_handler)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

MAX_RETRIES = 1  # 1 initial + 1 retry = 2 attempts max
_TRANSIENT_EXIT_CODES = {125, 130, 137, 143}  # container timeout, OOM, kill
DEFAULT_CLI_PATH = "agent_orchestrator"
AO_CLI_PATH_ENV = "AO_CLI_PATH"


# ---------------------------------------------------------------------------
# Path resolution
# ---------------------------------------------------------------------------

def resolve_cli_path(cli_path: str | None = None) -> str:
    """Resolve AO CLI path from env, explicit arg, or default name.

    Priority:
      1. Explicit *cli_path* argument (if given)
      2. ``AO_CLI_PATH`` environment variable
      3. Default ``agent_orchestrator``
    """
    if cli_path:
        return cli_path
    env = os.environ.get(AO_CLI_PATH_ENV, "").strip()
    if env:
        return env
    return DEFAULT_CLI_PATH


def find_cli_executable(cli_path: str) -> Optional[str]:
    """Locate an executable for *cli_path*.

    Supports:
      - bare command names on PATH (``agent_orchestrator``)
      - absolute paths
      - relative paths from CWD (e.g. ``scripts/agent_orchestrator``)
    """
    if not cli_path:
        return None

    path = Path(cli_path).expanduser()
    # Path with directory component (absolute or relative)
    if path.is_absolute() or os.sep in cli_path or (os.altsep and os.altsep in cli_path):
        if path.is_file() and os.access(path, os.X_OK):
            return str(path.resolve())
        # also try which for absolute paths that may be symlinks on PATH
        found = shutil.which(cli_path)
        return found

    return shutil.which(cli_path)


# ---------------------------------------------------------------------------
# AOResult — structured result container
# ---------------------------------------------------------------------------

class AOResult:
    """Structured result from an AO CLI invocation.

    Used by ``AgentAdapter.invoke()`` and ``AOClient.invoke()``.
    Attributes match what ``adapter.py`` expects:
      - ``success`` (bool): True if exit_code == 0
      - ``text`` (str): stdout content (strip()'ed)
      - ``exit_code`` (int): process exit code
      - ``stderr`` (str): stderr content
      - ``elapsed`` (float): seconds the process ran
    """

    def __init__(self, stdout: str = "", stderr: str = "",
                 exit_code: int = 0, elapsed: float = 0.0):
        self.stdout = stdout
        self.stderr = stderr
        self.exit_code = exit_code
        self.elapsed = elapsed

    @classmethod
    def error(cls, stderr: str = "", stdout: str = "",
              elapsed: float = 0.0) -> "AOResult":
        return cls(stdout=stdout, stderr=stderr, exit_code=1, elapsed=elapsed)

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    @property
    def text(self) -> str:
        """Best-effort response text from stdout, stripped."""
        return self.stdout.strip()

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"<AOResult {status} exit={self.exit_code}>"

    @classmethod
    def from_run_result(cls, run_result: dict) -> "AOResult":
        """Convert a ``run_agent()`` dict into an ``AOResult``."""
        return cls(
            stdout=run_result.get("output", ""),
            stderr=run_result.get("error", ""),
            exit_code=run_result.get("return_code", 1),
            elapsed=run_result.get("elapsed", 0.0),
        )


# ---------------------------------------------------------------------------
# AOClient — primary class ใช้โดย adapter.py
# ---------------------------------------------------------------------------

class AOClient:
    """Client สำหรับเรียก AO CLI ผ่าน subprocess

    Primary interface used by ``AgentAdapter.invoke()`` in adapter.py.

    Attributes:
        cli_path:        Path หรือ command name ของ AO CLI binary
        default_timeout: Default timeout วินาที (sec)
    """

    def __init__(self, cli_path: str | None = None, timeout: int = 120):
        self.cli_path = resolve_cli_path(cli_path)
        self.default_timeout = timeout
        self._cli_path = self.cli_path  # For backward compat with get_ao_status

    # ------------------------------------------------------------------
    # Availability check
    # ------------------------------------------------------------------

    def resolved_path(self) -> Optional[str]:
        """Return absolute executable path if available, else None."""
        return find_cli_executable(self.cli_path)

    def check_available(self) -> bool:
        """ตรวจสอบว่า AO CLI binary พร้อมใช้งาน (PATH หรือ path ใน config)"""
        found = self.resolved_path()
        available = found is not None
        log.info("AO CLI '%s' available: %s (%s)", self.cli_path, available, found)
        return available

    # ------------------------------------------------------------------
    # invoke() — ใช้โดย AgentAdapter
    # ------------------------------------------------------------------

    def invoke(
        self,
        prompt: str,
        agent_type: str = "default",
        timeout: Optional[int] = None,
        agent_args: Optional[list[str]] = None,
    ) -> AOResult:
        """Invoke AO CLI (interface สำหรับ AgentAdapter).

        Args:
            prompt:     Full prompt string
            agent_type: Agent type identifier
            timeout:    Max seconds (default: self.default_timeout)
            agent_args: Extra CLI arguments (optional)

        Returns:
            AOResult
        """
        run_result = self.run_agent(agent_type, prompt, timeout=timeout)
        return AOResult.from_run_result(run_result)

    # ------------------------------------------------------------------
    # run_agent — simplified API (returns dict)
    # ------------------------------------------------------------------

    def run_agent(
        self,
        agent_id: str,
        prompt: str,
        timeout: Optional[int] = None,
    ) -> dict:
        """เรียก AO CLI spawn agent (API ง่ายกว่า invoke)

        Args:
            agent_id: ID ของ agent (ceo, orchestrator, architect, ฯลฯ)
            prompt:  ข้อความ prompt
            timeout: timeout วินาที (default: self.default_timeout)

        Returns:
            dict: {success, output, error, elapsed, return_code}
        """
        effective_timeout = timeout or self.default_timeout
        log.info("run_agent: agent=%s timeout=%ds", agent_id, effective_timeout)

        start = time.monotonic()
        last_output = ""
        last_error = ""
        return_code = -1

        attempts = 1 + MAX_RETRIES
        for attempt in range(1, attempts + 1):
            if attempt > 1:
                log.info("Retry %d/%d for '%s'", attempt, attempts, agent_id)
                time.sleep(1 * attempt)

            try:
                exe = self.resolved_path() or self.cli_path
                proc = subprocess.run(
                    [exe, "run", agent_id, "--prompt", prompt],
                    capture_output=True,
                    text=True,
                    timeout=effective_timeout,
                )
                return_code = proc.returncode
                last_output = proc.stdout
                last_error = proc.stderr

                if return_code == 0:
                    elapsed = round(time.monotonic() - start, 3)
                    log.info("Agent '%s' OK (exit=0, %.2fs)", agent_id, elapsed)
                    return {
                        "success": True,
                        "output": proc.stdout,
                        "error": proc.stderr,
                        "elapsed": elapsed,
                        "return_code": 0,
                    }

                log.warning("Agent '%s' exit=%d (attempt %d): %.200s",
                            agent_id, return_code, attempt, proc.stderr.strip())
                if return_code not in _TRANSIENT_EXIT_CODES:
                    break

            except subprocess.TimeoutExpired:
                elapsed = round(time.monotonic() - start, 3)
                log.error("Agent '%s' TIMEOUT after %ds", agent_id, effective_timeout)
                last_error = f"TIMEOUT_EXPIRED after {effective_timeout}s"
                return_code = -9
                break

            except FileNotFoundError:
                elapsed = round(time.monotonic() - start, 3)
                log.error("CLI '%s' not found", self.cli_path)
                return {
                    "success": False, "output": "", "error":
                        f"AO CLI '{self.cli_path}' not found.",
                    "elapsed": elapsed, "return_code": -1,
                }

            except Exception as exc:
                log.error("Unexpected error for '%s': %s", agent_id, exc)
                last_error = str(exc)
                continue

        elapsed = round(time.monotonic() - start, 3)
        log.error("Agent '%s' FAILED after %.2fs (exit=%d)", agent_id, elapsed, return_code)
        return {
            "success": False,
            "output": last_output,
            "error": last_error,
            "elapsed": elapsed,
            "return_code": return_code,
        }

    # ------------------------------------------------------------------
    # Status / introspection
    # ------------------------------------------------------------------

    def get_status(self) -> dict:
        """ตรวจสอบสถานะ AO CLI

        Returns:
            dict: {available, cli_path, version, error}
        """
        resolved = self.resolved_path()
        if not resolved:
            return {
                "available": False,
                "cli_path": self.cli_path,
                "version": None,
                "error": (
                    f"AO CLI '{self.cli_path}' not found. "
                    f"Set {AO_CLI_PATH_ENV} or cli_path in gov/ao_config.toml"
                ),
            }

        version: Optional[str] = None
        try:
            result = subprocess.run(
                [resolved, "--version"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode == 0:
                version = (result.stdout or result.stderr).strip()
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            pass

        return {
            "available": True,
            "cli_path": resolved,
            "version": version,
            "error": None,
        }

    def list_agents(self) -> list[dict]:
        """List available agents จาก AO CLI

        Returns:
            list[dict]: แต่ละ agent มี key ``name``
        """
        exe = self.resolved_path() or self.cli_path
        try:
            result = subprocess.run(
                [exe, "list"],
                capture_output=True, text=True, timeout=10,
            )
            if result.returncode != 0:
                log.warning("list_agents failed (exit=%d)", result.returncode)
                return []

            # Try JSON first
            try:
                agents = json.loads(result.stdout)
                if isinstance(agents, list):
                    return agents
            except json.JSONDecodeError:
                pass

            # Fallback: text lines
            lines = [l.strip() for l in result.stdout.splitlines() if l.strip()]
            return [{"name": line} for line in lines]

        except (subprocess.TimeoutExpired, FileNotFoundError, OSError) as exc:
            log.error("list_agents error: %s", exc)
            return []


# ---------------------------------------------------------------------------
# AOCliClient — legacy alias (backward compat สำหรับ bridge integration)
# ---------------------------------------------------------------------------

class AOCliClient(AOClient):
    """Legacy alias for ``AOClient``.  Provides backward compatibility.

    ``bridge_integration.py`` and ``govctl_cli.cli`` may reference
    ``AOCliClient`` — this class ensures those imports still work.
    """


# ---------------------------------------------------------------------------
# Shortcut: get_configured_client
# ---------------------------------------------------------------------------

def get_configured_client(config_path: Optional[Path] = None) -> AOClient:
    """สร้าง AOClient จาก ao_config.toml + AO_CLI_PATH env override."""
    config = _load_config(config_path)
    ao_cfg = config.get("ao", {})
    # Env wins over config (ops override without editing TOML)
    env_path = os.environ.get(AO_CLI_PATH_ENV, "").strip()
    cli_path = env_path or ao_cfg.get("cli_path") or DEFAULT_CLI_PATH
    return AOClient(
        cli_path=cli_path,
        timeout=int(ao_cfg.get("timeout_seconds", 120)),
    )


def _load_config(config_path: Optional[Path] = None) -> dict:
    """Load TOML config, return empty dict if not found."""
    if config_path is None:
        config_path = Path("gov") / "ao_config.toml"
    try:
        import tomllib
        with open(config_path, "rb") as f:
            return tomllib.load(f)
    except (FileNotFoundError, tomllib.TOMLDecodeError, ImportError):
        return {}
