"""Development server for the API:  python -m winetracker.api

Reloads when code under ``src`` changes. File watching uses polling (comparing
modified times) because OneDrive and similar sync tools constantly update file
attributes, which the default event-based watcher reports as edits.
"""

from __future__ import annotations

import os
from pathlib import Path

import uvicorn

SRC_DIR = Path(__file__).resolve().parents[2]


def main() -> None:
    os.environ.setdefault("WATCHFILES_FORCE_POLLING", "true")
    uvicorn.run(
        "winetracker.api.main:app",
        host=os.environ.get("HOST", "127.0.0.1"),
        port=int(os.environ.get("PORT", "8000")),
        reload=True,
        reload_dirs=[str(SRC_DIR)],
    )


if __name__ == "__main__":
    main()
