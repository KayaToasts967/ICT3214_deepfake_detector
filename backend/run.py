"""Common native/container launcher with literal local .env settings."""
import argparse
import os
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def load_local_environment(path: Path):
    if not path.exists():
        return
    for number, raw in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not separator or not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", key):
            raise ValueError(f"Invalid .env entry on line {number}; use NAME=value.")
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        # Values are literal. Never evaluate shell commands or interpolate secrets.
        os.environ.setdefault(key, value)


def main():
    os.chdir(ROOT)
    load_local_environment(ROOT / ".env")
    parser = argparse.ArgumentParser(description="Run VoiceScope on this computer.")
    parser.add_argument("--port", type=int)
    parser.add_argument("--container", action="store_true", help="Container-internal interface; use Compose for loopback publishing.")
    args = parser.parse_args()
    try:
        port = args.port if args.port is not None else int(os.getenv("VOICE_SCOPE_PORT", "8000"))
    except ValueError:
        parser.error("VOICE_SCOPE_PORT must be an integer.")
    if not 1 <= port <= 65535:
        parser.error("Port must be between 1 and 65535.")
    host = "0.0.0.0" if args.container else "127.0.0.1"
    print(f"VoiceScope local dashboard: http://127.0.0.1:{port}", flush=True)
    import uvicorn
    uvicorn.run("backend.main:app", host=host, port=port, workers=1)


if __name__ == "__main__":
    main()
