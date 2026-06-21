"""Put the project root on sys.path so `from options.x import y` works without an install."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
