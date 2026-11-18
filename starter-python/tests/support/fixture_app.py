"""Test harness: runs the app as a real subprocess with an isolated fixture directory.

Used by acceptance tests and by the harness's own unit tests. Never points at a
real database: every instance gets its own DATA_DIR and a free loopback port.
"""
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2]
READY_TIMEOUT_SECONDS = 10.0
STOP_TIMEOUT_SECONDS = 5.0


def free_port() -> int:
    """Return a loopback port that was free when asked."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


class FixtureApp:
    """One app instance with its own fixture state. Not shared between tests."""

    def __init__(self, data_dir: Path, app_dir: Path = APP_DIR) -> None:
        self.data_dir = Path(data_dir)
        self.app_dir = Path(app_dir)
        self.port = free_port()
        self.process: subprocess.Popen | None = None
        self._log_file = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def log_path(self) -> Path:
        return self.data_dir.parent / f"{self.data_dir.name}-app.log"

    def _env(self) -> dict:
        env = dict(os.environ)
        env["DATA_DIR"] = str(self.data_dir)
        env["PORT"] = str(self.port)
        return env

    def reset(self) -> None:
        """Explicit fixture reset. Only ever touches self.data_dir."""
        subprocess.run(
            [sys.executable, "app.py", "--reset"],
            cwd=self.app_dir,
            env=self._env(),
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )

    def start(self) -> None:
        if self.process is not None and self.process.poll() is None:
            raise RuntimeError("app is already running")
        self._log_file = open(self.log_path, "a", encoding="utf-8")
        self.process = subprocess.Popen(
            [sys.executable, "app.py"],
            cwd=self.app_dir,
            env=self._env(),
            stdout=self._log_file,
            stderr=subprocess.STDOUT,
        )
        self._wait_until_ready()

    def _wait_until_ready(self) -> None:
        deadline = time.monotonic() + READY_TIMEOUT_SECONDS
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"app exited during startup with {self.process.returncode}; "
                    f"see {self.log_path}"
                )
            try:
                status, _ = self.request("GET", "/health")
                if status == 200:
                    return
            except OSError:
                pass
            time.sleep(0.05)
        self.stop()
        raise RuntimeError(f"app did not become ready; see {self.log_path}")

    def stop(self) -> int | None:
        """Stop the process if running. Returns its exit code, or None if never started."""
        if self.process is None:
            return None
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=STOP_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        code = self.process.returncode
        if self._log_file is not None:
            self._log_file.close()
            self._log_file = None
        return code

    def request(self, method: str, path: str, *, json_body=None, raw: bytes | None = None):
        """Send one HTTP request. Returns (status, parsed JSON or text).

        Non-2xx responses are returned, not raised. Connection failures raise OSError.
        """
        data = raw
        headers = {}
        if json_body is not None:
            data = json.dumps(json_body).encode("utf-8")
        if data is not None:
            headers["Content-Type"] = "application/json"
        req = urllib.request.Request(
            self.base_url + path, data=data, method=method, headers=headers
        )
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                status, body = response.status, response.read()
        except urllib.error.HTTPError as error:
            status, body = error.code, error.read()
        text = body.decode("utf-8", errors="replace")
        try:
            return status, json.loads(text)
        except json.JSONDecodeError:
            return status, text

    def __enter__(self) -> "FixtureApp":
        return self

    def __exit__(self, *exc) -> None:
        self.stop()
