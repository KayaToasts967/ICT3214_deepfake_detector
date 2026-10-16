"""Idempotent Windows setup; nothing is uploaded or published."""
from pathlib import Path
import shutil
import subprocess
import sys
import venv

ROOT = Path(__file__).resolve().parents[1]


def main():
    if sys.platform != "win32":
        raise SystemExit("This setup script supports Windows only.")
    if sys.version_info[:2] != (3, 12):
        raise SystemExit("Use Python 3.12 for the tested dependency lock, or use Docker Compose.")
    environment = ROOT / ".venv"
    executable = environment / "Scripts/python.exe"
    if not executable.exists():
        print("Creating .venv", flush=True)
        venv.EnvBuilder(with_pip=True).create(environment)
    subprocess.run([str(executable), "-m", "pip", "install", "--disable-pip-version-check",
                    "-r", str(ROOT / "requirements.lock.txt"), "-r", str(ROOT / "requirements-model.txt")], check=True)
    local_env = ROOT / ".env"
    if not local_env.exists():
        shutil.copyfile(ROOT / ".env.example", local_env)
    print("Setup complete. Start: .\\.venv\\Scripts\\python.exe -m backend.run", flush=True)
    print("Dashboard: http://127.0.0.1:8000 (or VOICE_SCOPE_PORT in .env)", flush=True)


if __name__ == "__main__":
    main()
