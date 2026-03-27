"""Entry point: drawiterm [filename]"""
from __future__ import annotations

import sys
from pathlib import Path

from .app import DrawitermApp


def main() -> None:
    filepath = Path(sys.argv[1]) if len(sys.argv) > 1 else None
    app = DrawitermApp(filepath=filepath)
    app.run()


if __name__ == "__main__":
    main()
