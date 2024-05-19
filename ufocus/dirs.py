# -*- coding: utf-8 -*-

from pathlib import Path

BASE_PATH: Path = Path.home() / "Documents" / "uFocus"
BASE_DATA_PATH: Path = BASE_PATH / "data"
LOGS_PATH: Path = BASE_PATH / "logs"
PLUGIN_PATH_CAMERA = Path(".") / "ufocus" / "extensions"


def create_dir(path: Path):
    if not path.exists():
        path.mkdir(parents=True)
