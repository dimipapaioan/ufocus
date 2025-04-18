# -*- coding: utf-8 -*-

from pathlib import Path

BASE_PATH: Path = Path.home() / "Documents" / "uFocus"
BASE_DATA_PATH: Path = BASE_PATH / "data"
LOGS_PATH: Path = BASE_PATH / "logs"


def create_dir(path: Path) -> None:
    if not path.exists():
        path.mkdir(parents=True)


for path in (BASE_PATH, BASE_DATA_PATH, LOGS_PATH):
    create_dir(path)
