#!/usr/bin/env python3
"""Kept for existing callers: `bark_config.py show | set FIELD VALUE | reset` = `xxd_notify.py config …`."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from xxd_notify import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main(["config", *sys.argv[1:]]))
