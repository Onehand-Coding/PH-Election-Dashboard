from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    app_path = Path(__file__).resolve().parent / "app.py"
    src_path = str(app_path.parent.parent)
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = src_path if not existing else src_path + os.pathsep + existing
    try:
        return subprocess.call(
            [sys.executable, "-m", "streamlit", "run", str(app_path)],
            env=env,
        )
    except KeyboardInterrupt:
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
