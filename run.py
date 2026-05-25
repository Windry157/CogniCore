#!/usr/bin/env python3
"""
CogniCore Portable - Unified Launcher
Insert USB -> python run.py -> everything starts.
Supports Windows / Linux / Android (Termux) / macOS.
"""

import sys
import os
import platform
import subprocess
import time
import signal
import json
import webbrowser
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COGNICORE = ROOT / "cognicore"
PID_FILE = ROOT / ".cognicore_pid"
OLLAMA_PID_FILE = ROOT / ".ollama_pid"
PORT = 8002
HOST = "127.0.0.1"
P_NAME = "CogniCore"


def detect_os():
    s = platform.system().lower()
    if s == "windows":
        return "windows"
    if s == "linux" and "android" in platform.platform().lower():
        return "android"
    if s == "linux":
        return "linux"
    if s == "darwin":
        return "darwin"
    return s


def find_python():
    py_dir = ROOT / "python"
    if detect_os() == "windows":
        candidates = [
            py_dir / "python.exe",
            py_dir / "python" / "python.exe",
            Path(sys.prefix) / "python.exe",
        ]
    else:
        candidates = [
            py_dir / "bin" / "python3",
            py_dir / "python3",
            Path(sys.prefix) / "bin" / "python3",
        ]
    for c in candidates:
        if c.is_file():
            return str(c)
    return sys.executable


def find_pip(python):
    if detect_os() == "windows":
        return str(Path(python).parent / "Scripts" / "pip.exe")
    return str(Path(python).parent / "pip3")


def ensure_venv(python):
    venv_dir = ROOT / "venv"
    if venv_dir.is_dir():
        if detect_os() == "windows":
            py = str(venv_dir / "Scripts" / "python.exe")
        else:
            py = str(venv_dir / "bin" / "python3")
        if Path(py).is_file():
            return py
    if subprocess.run([python, "-c", "import venv"], capture_output=True).returncode != 0:
        return python
    print("[setup] Creating virtual environment...")
    subprocess.run([python, "-m", "venv", str(venv_dir)], check=True)
    return ensure_venv(python)


def install_deps(python):
    req = COGNICORE / "requirements.txt"
    if not req.is_file():
        return
    if subprocess.run([python, "-c", "import fastapi"], capture_output=True).returncode == 0:
        return
    print("[setup] Installing dependencies...")
    subprocess.run(
        f'"{python}" -m pip install -r "{req}"',
        timeout=120, shell=True,
    )


def find_ollama():
    os_name = detect_os()
    if os_name == "windows":
        bin_name = "ollama.exe"
    else:
        bin_name = "ollama"
    candidates = [
        ROOT / "ollama" / bin_name,
        ROOT / "ollama" / f"ollama-{os_name}",
        ROOT / "ollama" / f"ollama-{os_name}.exe",
    ]
    for c in candidates:
        if c.is_file():
            return str(c.resolve())
    which = shutil_which("ollama")
    if which:
        return which
    return None


def shutil_which(name):
    try:
        import shutil
        return shutil.which(name)
    except Exception:
        return None


PYTHON_EMBED_URL = "https://www.python.org/ftp/python/3.12.9/python-3.12.9-embed-amd64.zip"


def ensure_embedded_python():
    py_dir = ROOT / "python"
    if (py_dir / "python.exe").is_file():
        return str(py_dir / "python.exe")
    print("[setup] Downloading portable Python 3.12...")
    zip_path = ROOT / "python-embed.zip"
    try:
        urllib.request.urlretrieve(PYTHON_EMBED_URL, zip_path)
        with zipfile.ZipFile(zip_path, "r") as z:
            z.extractall(py_dir)
        zip_path.unlink(missing_ok=True)
        pth = list(py_dir.glob("python*._pth"))
        if pth:
            pth[0].write_text(pth[0].read_text(encoding="utf-8").replace("#import site", "import site"), encoding="utf-8")
        print("[setup] Portable Python ready")
        py_exe = str(py_dir / "python.exe")
        # Install pip
        pip_url = "https://bootstrap.pypa.io/get-pip.py"
        pip_path = ROOT / "get-pip.py"
        try:
            urllib.request.urlretrieve(pip_url, pip_path)
            subprocess.run([py_exe, str(pip_path), "--quiet"], timeout=60)
            pip_path.unlink(missing_ok=True)
            print("[setup] pip installed")
        except Exception as e:
            print(f"[setup] pip install skipped: {e}")
            pip_path.unlink(missing_ok=True)
        return py_exe
    except Exception as e:
        print(f"[setup] Python download failed: {e}")
        zip_path.unlink(missing_ok=True)
        return None


def start_ollama(ollama_path):
    os_name = detect_os()
    log = ROOT / "logs" / "ollama.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["OLLAMA_HOST"] = "127.0.0.1"
    env["OLLAMA_MODELS"] = str(ROOT / "models")
    try:
        if os_name == "windows":
            proc = subprocess.Popen(
                [ollama_path, "serve"],
                stdout=open(log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
                env=env, creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            proc = subprocess.Popen(
                [ollama_path, "serve"],
                stdout=open(log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
                env=env,
            )
        with open(OLLAMA_PID_FILE, "w") as f:
            f.write(str(proc.pid))
        print(f"  Ollama started (PID {proc.pid})")
        time.sleep(2)
        return proc.pid
    except Exception as e:
        print(f"  [warn] Ollama start failed: {e}")
        return None


def ensure_model(ollama_path):
    default = "qwen2.5:0.5b"
    try:
        r = subprocess.run(
            [ollama_path, "list"], capture_output=True, text=True, timeout=10
        )
        if default not in r.stdout:
            print(f"[model] Pulling {default} (~300MB)...")
            subprocess.run([ollama_path, "pull", default], timeout=600)
    except Exception:
        print(f"  [warn] Could not check/pull model")


def start_cognicore(python):
    log = ROOT / "logs" / "cognicore.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    app_script = str(COGNICORE / "app.py")
    env = os.environ.copy()
    env["CONFIG_PATH"] = str(ROOT / "config" / "cognicore.yaml")
    env["LLM_OLLAMA_BASE_URL"] = env.get("LLM_OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    os_name = detect_os()
    try:
        if os_name == "windows":
            proc = subprocess.Popen(
                [python, app_script, "--port", str(PORT), "--host", HOST],
                stdout=open(log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
                env=env, creationflags=subprocess.CREATE_NO_WINDOW,
            )
        else:
            proc = subprocess.Popen(
                [python, app_script, "--port", str(PORT), "--host", HOST],
                stdout=open(log, "w", encoding="utf-8"), stderr=subprocess.STDOUT,
                env=env,
            )
        with open(PID_FILE, "w") as f:
            f.write(str(proc.pid))
        print(f"  {P_NAME} started (PID {proc.pid})")
        return proc.pid
    except Exception as e:
        print(f"  [error] Failed to start {P_NAME}: {e}")
        sys.exit(1)


def wait_for_ready():
    import urllib.request
    for i in range(30):
        try:
            r = urllib.request.urlopen(f"http://{HOST}:{PORT}/health", timeout=2)
            if r.status == 200:
                return True
        except Exception:
            pass
        time.sleep(1)
    return False


def stop_process(pid_file):
    if not pid_file.is_file():
        return False
    try:
        pid = int(pid_file.read_text().strip())
        os.kill(pid, signal.SIGTERM if hasattr(signal, "SIGTERM") else 9)
    except Exception:
        pass
    pid_file.unlink(missing_ok=True)
    return True


def check_ollama(base):
    import urllib.request
    try:
        r = urllib.request.urlopen(f"{base}/api/tags", timeout=2)
        if r.status == 200:
            return base
    except Exception:
        pass
    return None

def cmd_start():
    ensure_embedded_python()
    python = find_python()
    print(f"  Python: {python}")
    python = ensure_venv(python)
    install_deps(python)
    models_dir = ROOT / "models"
    ollama_url = check_ollama("http://192.168.3.105:11434")
    if ollama_url:
        print(f"  Ollama: remote ({ollama_url})")
    else:
        ollama_url = check_ollama("http://127.0.0.1:11434")
        if ollama_url:
            print(f"  Ollama: local (already running at {ollama_url})")
        else:
            ollama_path = find_ollama()
            if ollama_path:
                print(f"  Ollama: USB ({ollama_path})")
                os.environ["OLLAMA_MODELS"] = str(models_dir)
                start_ollama(ollama_path)
                ensure_model(ollama_path)
                ollama_url = "http://127.0.0.1:11434"
            else:
                print("  [warn] Ollama not found - AI chat offline")
    if ollama_url:
        os.environ["LLM_OLLAMA_BASE_URL"] = ollama_url
        os.environ["LLM_OLLAMA_MODEL"] = "qwen2.5:0.5b"
    start_cognicore(python)
    ready = wait_for_ready()
    if ready:
        print(f"\n  [OK] {P_NAME} running at http://{HOST}:{PORT}")
        webbrowser.open(f"http://{HOST}:{PORT}/launcher")
    else:
        print(f"\n  [!] {P_NAME} started but not yet ready - check logs/")
    print("  Press Ctrl+C to stop all services")
    try:
        signal.pause() if hasattr(signal, "pause") else time.sleep(99999)
    except KeyboardInterrupt:
        cmd_stop()


def cmd_stop():
    print(f"Stopping {P_NAME}...")
    stop_process(PID_FILE)
    stop_process(OLLAMA_PID_FILE)
    print("  Stopped")


def cmd_status():
    def is_running(pid_file, name):
        if not pid_file.is_file():
            print(f"  {name}: stopped")
            return
        try:
            pid = int(pid_file.read_text().strip())
            os.kill(pid, 0)
            print(f"  {name}: running (PID {pid})")
        except Exception:
            print(f"  {name}: stopped (stale PID)")
            pid_file.unlink(missing_ok=True)

    is_running(PID_FILE, P_NAME)
    is_running(OLLAMA_PID_FILE, "Ollama")


def cmd_info():
    print(f"CogniCore Portable v2.1.0")
    print(f"  Root:     {ROOT}")
    print(f"  OS:       {detect_os()}")
    print(f"  Python:   {find_python()}")
    ollama_path = find_ollama()
    print(f"  Ollama:   {ollama_path or 'not found'}")
    print(f"  Port:     {PORT}")
    print(f"\n  Commands:")
    print(f"    python run.py           Start all services")
    print(f"    python run.py --stop    Stop all services")
    print(f"    python run.py --status  Check running status")
    print(f"    python run.py --info    Show system info")


def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        if arg in ("--stop", "-s"):
            return cmd_stop()
        if arg in ("--status", "-st"):
            return cmd_status()
        if arg in ("--info", "-i"):
            return cmd_info()
        if arg in ("--help", "-h"):
            cmd_info()
            return
    print(f"=" * 56)
    print(f"  CogniCore Portable v2.1.0")
    print(f"  Unified Launcher")
    print(f"=" * 56)
    print()
    cmd_start()


if __name__ == "__main__":
    main()
