from pathlib import Path
from shutil import copy2

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "backend" / "static"
DESTINATION = ROOT / "public" / "static"

for source_path in SOURCE.rglob("*"):
    relative_path = source_path.relative_to(SOURCE)
    if not source_path.is_file() or "uploads" in relative_path.parts:
        continue

    destination_path = DESTINATION / relative_path
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    copy2(source_path, destination_path)
