from __future__ import annotations
import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env on import
load_dotenv()


def get_output_dir(base: str = "outputs") -> str:
    Path(base).mkdir(parents=True, exist_ok=True)
    return base
