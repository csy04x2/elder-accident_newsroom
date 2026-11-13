"""Entry point for Windows Task Scheduler; ensure repo is importable."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from newsroom.daily_update import main

if __name__ == "__main__":
    main()
