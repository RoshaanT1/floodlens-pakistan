"""Root conftest: ensure the project root is on sys.path for all tests."""
import sys
from pathlib import Path

# Add the project root so `from src.xxx import yyy` works without pip install -e .
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
