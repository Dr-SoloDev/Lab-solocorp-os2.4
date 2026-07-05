"""
Unit tests for govctl_cli/api_cli.py — process management CLI commands.

All system calls (os.kill, subprocess.Popen, time.sleep, etc.) are mocked.
PID_FILE and LOG_FILE are redirected to tmp_path for isolation.
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

import govctl_cli.api_cli as api_mod

# ===========================================================================
# _read_pid
# ===========================================================================


class TestReadPid:
    """_read_pid() — reads PID from PID_FILE."""

    def test_read_pid_exists_valid(self, monkeypatch, tmp_path):
        """PID_FILE exists with valid numeric content → returns the int."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("12345")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        assert api_mod._read_pid() == 12345

    def test_read_pid_exists_invalid(self, monkeypatch, tmp_path):
        """PID_FILE exists but content is non-numeric → returns None."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("abc")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        assert api_mod._read_pid() is None

    def test_read_pid_exists_empty(self, monkeypatch, tmp_path):
        """PID_FILE exists but is empty after strip → returns None."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("   \n")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        assert api_mod._read_pid() is None

    def test_read_pid_not_exists(self, monkeypatch, tmp_path):
        """PID_FILE does not exist → returns None."""
        pid_file = tmp_path / "api.pid"  # deliberately not created
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        assert api_mod._read_pid() is None

    def test_read_pid_oserror(self, monkeypatch, tmp_path):
        """OSError during read (e.g. permission denied) → returns None."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("12345")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        # Patch at the Path class level (PosixPath instance methods are read-only)
        with patch.object(Path, "read_text", side_effect=OSError("permission denied")):
            assert api_mod._read_pid() is None


# ===========================================================================
# _is_running
# ===========================================================================


class TestIsRunning:
    """_is_running(pid) — checks process liveness via os.kill(pid, 0)."""

    def test_is_running_alive(self):
        """os.kill(pid, 0) succeeds → process is alive → returns True."""
        with patch("os.kill") as mock_kill:
            result = api_mod._is_running(12345)
        assert result is True
        mock_kill.assert_called_once_with(12345, 0)

    def test_is_running_dead(self):
        """os.kill(pid, 0) raises OSError → process is dead → returns False."""
        with patch("os.kill", side_effect=OSError("No such process")):
            result = api_mod._is_running(12345)
        assert result is False


# ===========================================================================
# _write_pid
# ===========================================================================


class TestWritePid:
    """_write_pid(pid) — writes PID string to PID_FILE."""

    def test_write_pid_writes(self, monkeypatch, tmp_path):
        """Writes str(pid) to PID_FILE."""
        pid_file = tmp_path / "api.pid"
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        api_mod._write_pid(99999)
        assert pid_file.read_text() == "99999"


# ===========================================================================
# _check_uvicorn
# ===========================================================================


class TestCheckUvicorn:
    """_check_uvicorn() — verifies uvicorn is importable (cached)."""

    def setup_method(self):
        """Reset the module-level cache before each test."""
        api_mod._UVICORN_AVAILABLE = None

    def test_check_uvicorn_installed(self):
        """uvicorn import succeeds → returns True and caches the result."""
        with patch("builtins.__import__") as mock_import:
            mock_import.return_value = MagicMock()
            assert api_mod._check_uvicorn() is True
            assert api_mod._UVICORN_AVAILABLE is True

    def test_check_uvicorn_not_installed(self):
        """uvicorn import raises ImportError → returns False and caches."""
        with patch("builtins.__import__", side_effect=ImportError("no module named uvicorn")):
            assert api_mod._check_uvicorn() is False
            assert api_mod._UVICORN_AVAILABLE is False

    def test_check_uvicorn_caches_result(self):
        """Second call reuses cached result without re-importing."""
        with patch("builtins.__import__") as mock_import:
            mock_import.return_value = MagicMock()
            # First call triggers __import__ twice: "subprocess" + "uvicorn"
            assert api_mod._check_uvicorn() is True
            # Second call must use cache, not import again
            assert api_mod._check_uvicorn() is True
            # Only 2 __import__ calls (both from the first invocation)
            assert mock_import.call_count == 2, (
                f"Expected 2 __import__ calls (subprocess + uvicorn), got {mock_import.call_count}"
            )


# ===========================================================================
# cmd_status
# ===========================================================================


class TestCmdStatus:
    """cmd_status() — returns running info dict and prints status."""

    def test_cmd_status_running(self, capsys, monkeypatch, tmp_path):
        """PID file exists and process alive → 'RUNNING' in output, running=True."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("98765")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        with patch.object(api_mod, "_is_running", return_value=True):
            info = api_mod.cmd_status()

        assert info["running"] is True
        assert info["pid"] == 98765
        assert info["pid_file"] == str(pid_file)
        assert info["port"] == api_mod.DEFAULT_PORT

        captured = capsys.readouterr()
        assert "RUNNING" in captured.out
        assert "98765" in captured.out

    def test_cmd_status_not_running_no_pid(self, capsys, monkeypatch, tmp_path):
        """No PID file → 'NOT running' in output, running=False, pid=None."""
        pid_file = tmp_path / "api.pid"  # not created
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        info = api_mod.cmd_status()

        assert info["running"] is False
        assert info["pid"] is None

        captured = capsys.readouterr()
        assert "NOT running" in captured.out

    def test_cmd_status_not_running_dead_pid(self, capsys, monkeypatch, tmp_path):
        """PID file exists but process dead → 'NOT running', running=False."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("98765")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        with patch.object(api_mod, "_is_running", return_value=False):
            info = api_mod.cmd_status()

        assert info["running"] is False
        assert info["pid"] is None

        captured = capsys.readouterr()
        assert "NOT running" in captured.out


# ===========================================================================
# cmd_stop
# ===========================================================================


class TestCmdStop:
    """cmd_stop() — stops the server via SIGTERM / SIGKILL."""

    def test_cmd_stop_no_pidfile(self, capsys, monkeypatch, tmp_path):
        """No PID file → early return with 'not running' message."""
        pid_file = tmp_path / "api.pid"  # not created
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        with (
            patch("os.kill") as mock_kill,
            patch("time.sleep") as mock_sleep,
        ):
            api_mod.cmd_stop()

        mock_kill.assert_not_called()
        mock_sleep.assert_not_called()

        captured = capsys.readouterr()
        assert "not running" in captured.out
        assert "PID" not in captured.out or "no PID file" in captured.out

    def test_cmd_stop_already_dead(self, capsys, monkeypatch, tmp_path):
        """PID exists but process dead → 'already dead', PID_FILE unlinked."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("12345")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        with (
            patch.object(api_mod, "_is_running", return_value=False),
            patch("os.kill") as mock_kill,
            patch("time.sleep") as mock_sleep,
        ):
            api_mod.cmd_stop()

        mock_kill.assert_not_called()
        mock_sleep.assert_not_called()
        assert not pid_file.exists()  # unlinked

        captured = capsys.readouterr()
        assert "already dead" in captured.out

    def test_cmd_stop_sigterm_ok(self, capsys, monkeypatch, tmp_path):
        """Running process stops on SIGTERM → SIGTERM sent, PID_FILE cleaned."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("12345")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        # side_effect: first _is_running call (alive check) → True,
        #              second _is_running call (loop check) → False (died on SIGTERM)
        with (
            patch.object(api_mod, "_is_running", side_effect=[True, False]),
            patch("os.kill") as mock_kill,
            patch("time.sleep") as mock_sleep,
        ):
            api_mod.cmd_stop()

        # SIGTERM was sent; SIGKILL was NOT sent
        mock_kill.assert_called_once_with(12345, signal.SIGTERM)
        mock_sleep.assert_called_once()  # one sleep before the break

        assert not pid_file.exists()  # PID_FILE was unlinked

        captured = capsys.readouterr()
        assert "Stopping" in captured.out
        assert "stopped" in captured.out

    def test_cmd_stop_sigterm_fallback_sigkill(self, capsys, monkeypatch, tmp_path):
        """SIGTERM does not stop process → fallback to SIGKILL."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("12345")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        # _is_running always returns True → loop exhausts → SIGKILL path
        with (
            patch.object(api_mod, "_is_running", return_value=True),
            patch("os.kill") as mock_kill,
            patch("time.sleep") as mock_sleep,
        ):
            api_mod.cmd_stop()

        assert mock_kill.call_args_list == [
            call(12345, signal.SIGTERM),
            call(12345, signal.SIGKILL),
        ]
        # 10 loop sleeps + 1 post-SIGKILL sleep
        assert mock_sleep.call_count == 11
        assert not pid_file.exists()

        captured = capsys.readouterr()
        assert "SIGTERM did not stop" in captured.out
        assert "SIGKILL" in captured.out
        assert "stopped" in captured.out


# ===========================================================================
# cmd_start
# ===========================================================================


class TestCmdStart:
    """cmd_start(port, reload) — starts uvicorn subprocess."""

    def test_cmd_start_uvicorn_not_installed(self, capsys, monkeypatch, tmp_path):
        """_check_uvicorn returns False → 'uvicorn is not installed' message."""
        pid_file = tmp_path / "api.pid"  # not created → _read_pid returns None
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        with patch.object(api_mod, "_check_uvicorn", return_value=False):
            api_mod.cmd_start()

        captured = capsys.readouterr()
        assert "uvicorn is not installed" in captured.out

    def test_cmd_start_already_running(self, capsys, monkeypatch, tmp_path):
        """PID exists and process alive → 'already running' message."""
        pid_file = tmp_path / "api.pid"
        pid_file.write_text("12345")
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)

        with (
            patch.object(api_mod, "_is_running", return_value=True),
            patch.object(api_mod, "_check_uvicorn") as mock_uvicorn,
        ):
            api_mod.cmd_start()

        mock_uvicorn.assert_not_called()  # short-circuits before uvicorn check
        captured = capsys.readouterr()
        assert "already running" in captured.out
        assert "12345" in captured.out

    def test_cmd_start_starts_subprocess(self, capsys, monkeypatch, tmp_path):
        """Uvicorn available & not running → starts subprocess, writes PID."""
        pid_file = tmp_path / "api.pid"
        log_file = tmp_path / "api.log"
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        monkeypatch.setattr(api_mod, "LOG_FILE", log_file)

        with (
            patch.object(api_mod, "_check_uvicorn", return_value=True),
            patch("govctl_cli.api_cli.subprocess", create=True) as mock_subprocess,
        ):
            mock_proc = MagicMock()
            mock_proc.pid = 77777
            mock_subprocess.Popen.return_value = mock_proc

            api_mod.cmd_start(port=8888, reload=True)

        # Subprocess Popen called with the right arguments
        mock_subprocess.Popen.assert_called_once()
        args, kwargs = mock_subprocess.Popen.call_args
        cmd = args[0]

        assert sys.executable in cmd
        assert "--port" in cmd
        port_idx = cmd.index("--port")
        assert cmd[port_idx + 1] == "8888"
        assert "--reload" in cmd
        assert kwargs.get("start_new_session") is True
        # stdout / stderr point to the same LOG_FILE handle
        assert kwargs.get("stdout") is not None
        assert kwargs.get("stderr") is not None

        # PID was persisted
        assert pid_file.read_text() == "77777"

        captured = capsys.readouterr()
        assert "77777" in captured.out
        assert "8888" in captured.out

    def test_cmd_start_default_port(self, capsys, monkeypatch, tmp_path):
        """Default port 8765 is used when no port argument is given."""
        pid_file = tmp_path / "api.pid"
        log_file = tmp_path / "api.log"
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        monkeypatch.setattr(api_mod, "LOG_FILE", log_file)

        with (
            patch.object(api_mod, "_check_uvicorn", return_value=True),
            patch("govctl_cli.api_cli.subprocess", create=True) as mock_subprocess,
        ):
            mock_proc = MagicMock()
            mock_proc.pid = 88888
            mock_subprocess.Popen.return_value = mock_proc

            api_mod.cmd_start()  # no port → DEFAULT_PORT (8765)

        mock_subprocess.Popen.assert_called_once()
        cmd = mock_subprocess.Popen.call_args[0][0]
        port_idx = cmd.index("--port")
        assert cmd[port_idx + 1] == "8765"
        assert "--reload" not in cmd  # reload defaults to False

        captured = capsys.readouterr()
        assert "8765" in captured.out

    def test_cmd_start_no_reload_by_default(self, capsys, monkeypatch, tmp_path):
        """--reload defaults to False and is absent from command."""
        pid_file = tmp_path / "api.pid"
        log_file = tmp_path / "api.log"
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        monkeypatch.setattr(api_mod, "LOG_FILE", log_file)

        with (
            patch.object(api_mod, "_check_uvicorn", return_value=True),
            patch("govctl_cli.api_cli.subprocess", create=True) as mock_subprocess,
        ):
            mock_proc = MagicMock()
            mock_proc.pid = 99999
            mock_subprocess.Popen.return_value = mock_proc

            api_mod.cmd_start(reload=False)

        cmd = mock_subprocess.Popen.call_args[0][0]
        assert "--reload" not in cmd


# ===========================================================================
# _start_server
# ===========================================================================


class TestStartServer:
    """_start_server() — low-level subprocess launch."""

    def test_start_server_writes_pid_and_logs(self, capsys, monkeypatch, tmp_path):
        """_start_server opens LOG_FILE, spawns Popen, writes PID."""
        pid_file = tmp_path / "api.pid"
        log_file = tmp_path / "api.log"
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        monkeypatch.setattr(api_mod, "LOG_FILE", log_file)

        with patch("govctl_cli.api_cli.subprocess", create=True) as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.pid = 55555
            mock_subprocess.Popen.return_value = mock_proc

            api_mod._start_server(port=9999, reload=True)

        # Popen called
        mock_subprocess.Popen.assert_called_once()
        args, kwargs = mock_subprocess.Popen.call_args
        cmd = args[0]
        assert "govctl_cli.api.main:app" in cmd
        assert kwargs.get("start_new_session") is True

        # PID file written
        assert pid_file.read_text() == "55555"

        # Output printed
        captured = capsys.readouterr()
        assert "55555" in captured.out
        assert "9999" in captured.out
        assert str(log_file) in captured.out

    def test_start_server_without_reload(self, capsys, monkeypatch, tmp_path):
        """--reload flag is absent from command when reload=False."""
        pid_file = tmp_path / "api.pid"
        log_file = tmp_path / "api.log"
        monkeypatch.setattr(api_mod, "PID_FILE", pid_file)
        monkeypatch.setattr(api_mod, "LOG_FILE", log_file)

        with patch("govctl_cli.api_cli.subprocess", create=True) as mock_subprocess:
            mock_proc = MagicMock()
            mock_proc.pid = 66666
            mock_subprocess.Popen.return_value = mock_proc

            api_mod._start_server(reload=False)

        cmd = mock_subprocess.Popen.call_args[0][0]
        assert "--reload" not in cmd
        assert pid_file.read_text() == "66666"
