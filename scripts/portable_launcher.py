"""No-elevation Windows launcher for MAC Analyzer Pro.

The user-facing ``START_MAC_ANALYZER.cmd`` invokes this module with any
available Python.  The launcher then selects a Python installation that can
run the backend, starts it in a dedicated console, waits for the health check,
and opens the browser only after the application is ready.
"""

from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path
from typing import Iterable, Optional, Sequence, Tuple


REQUIRED_IMPORTS = "import openpyxl, xlrd, PIL, reportlab"


def _health(port: int, timeout: float = 0.8) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        return response.status == 200 and payload.get("status") == "ok"
    except (OSError, ValueError, urllib.error.URLError):
        return False


def _port_available(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        try:
            listener.bind(("127.0.0.1", port))
            return True
        except OSError:
            return False


def _candidate_commands(root: Path) -> Iterable[Tuple[Sequence[str], str]]:
    local_candidates = (
        root / ".venv-portable" / "Scripts" / "python.exe",
        root / ".venv" / "Scripts" / "python.exe",
        root / "runtime" / "python" / "python.exe",
    )
    for candidate in local_candidates:
        if candidate.is_file():
            yield ([str(candidate)], str(candidate))
    if sys.executable:
        yield ([sys.executable], sys.executable)
    yield (["py", "-3"], "py -3")
    yield (["python"], "python")


def _usable_python(root: Path) -> Tuple[Optional[Sequence[str]], str]:
    seen = set()
    probe = (
        "import sys; assert sys.version_info >= (3, 10); "
        + REQUIRED_IMPORTS
    )
    for command, label in _candidate_commands(root):
        key = tuple(str(part).lower() for part in command)
        if key in seen:
            continue
        seen.add(key)
        try:
            result = subprocess.run(
                [*command, "-c", probe],
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=12,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode == 0:
            return command, label
    return None, ""


def _select_port(preferred: int) -> int:
    if _health(preferred) or _port_available(preferred):
        return preferred
    for candidate in range(preferred + 1, min(65535, preferred + 20) + 1):
        if _port_available(candidate):
            return candidate
    raise RuntimeError(f"Не найден свободный локальный порт рядом с {preferred}.")


def _start_process(command: Sequence[str], root: Path, environment: dict, visible_console: bool) -> subprocess.Popen:
    creation_flags = 0
    stdout = None
    stderr = None
    if os.name == "nt":
        creation_flags |= getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
        creation_flags |= getattr(
            subprocess,
            "CREATE_NEW_CONSOLE" if visible_console else "CREATE_NO_WINDOW",
            0,
        )
    if not visible_console:
        log_directory = root / "logs"
        log_directory.mkdir(parents=True, exist_ok=True)
        stdout = (log_directory / "server.stdout.log").open("ab")
        stderr = (log_directory / "server.stderr.log").open("ab")
    try:
        return subprocess.Popen(
            list(command),
            cwd=str(root),
            env=environment,
            stdin=subprocess.DEVNULL,
            stdout=stdout,
            stderr=stderr,
            creationflags=creation_flags,
            start_new_session=os.name != "nt",
        )
    finally:
        if stdout is not None:
            stdout.close()
        if stderr is not None:
            stderr.close()


def launch(root: Path, preferred_port: int, no_browser: bool, hidden: bool) -> dict:
    root = root.resolve()
    server = root / "server.py"
    executable = root / "MACAnalyzerBackend.exe"
    if not server.is_file():
        raise FileNotFoundError(f"Не найден backend: {server}")

    port = _select_port(preferred_port)
    url = f"http://127.0.0.1:{port}/"
    if _health(port):
        if not no_browser:
            webbrowser.open(url, new=2)
        return {"status": "already-running", "url": url, "port": port}

    python_command, python_label = _usable_python(root)
    if python_command:
        command = [*python_command, str(server)]
        mode = f"Python console ({python_label})"
        visible_console = not hidden
    elif executable.is_file():
        command = [str(executable)]
        mode = "portable executable fallback (asInvoker)"
        visible_console = False
    else:
        raise RuntimeError(
            "Не найден Python 3.10+ с зависимостями и отсутствует переносимый backend. "
            "Используйте полный архив программы или установите requirements-web.txt."
        )

    runtime_directory = root / "data" / "runtime"
    runtime_directory.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment["MAC_ANALYZER_PORT"] = str(port)
    process = _start_process(command, root, environment, visible_console)
    deadline = time.monotonic() + 12.0
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Backend завершился при запуске, код {process.returncode}.")
        if _health(port):
            (runtime_directory / "server.pid").write_text(str(process.pid), encoding="ascii")
            if not no_browser:
                webbrowser.open(url, new=2)
            return {
                "status": "started",
                "url": url,
                "port": port,
                "pid": process.pid,
                "mode": mode,
                "administratorRightsRequired": False,
            }
        time.sleep(0.1)

    process.terminate()
    raise RuntimeError("Backend не прошёл проверку готовности в течение 12 секунд.")


def validate(root: Path) -> dict:
    root = root.resolve()
    python_command, python_label = _usable_python(root)
    return {
        "root": str(root),
        "server": (root / "server.py").is_file(),
        "index": (root / "index.html").is_file(),
        "launcher": (root / "START_MAC_ANALYZER.cmd").is_file(),
        "portableExecutable": (root / "MACAnalyzerBackend.exe").is_file(),
        "pythonBackend": bool(python_command),
        "python": python_label,
        "administratorRightsRequired": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Запуск MAC Analyzer Pro без прав администратора")
    parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--hidden", action="store_true", help="Скрыть отдельную Python-консоль")
    parser.add_argument("--validate-only", action="store_true")
    arguments = parser.parse_args()
    if not 1 <= arguments.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        report = validate(Path(arguments.root)) if arguments.validate_only else launch(
            Path(arguments.root), arguments.port, arguments.no_browser, arguments.hidden
        )
        # ASCII JSON keeps diagnostics readable even in legacy CMD code pages.
        print(json.dumps(report, ensure_ascii=True))
        return 0
    except Exception as error:  # user-facing launcher boundary
        print(f"MAC Analyzer Pro не запущен: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
