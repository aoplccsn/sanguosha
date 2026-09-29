from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


def main() -> int:
    executable = Path(sys.argv[1]).resolve()
    if not executable.is_file():
        raise SystemExit(f"missing executable: {executable}")
    environment = dict(os.environ)
    environment["SANGUOSHA_SMOKE_TEST"] = "1"
    process = subprocess.Popen([str(executable)], cwd=executable.parent, env=environment)
    try:
        return process.wait(timeout=30)
    except subprocess.TimeoutExpired:
        process.terminate()
        return process.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
