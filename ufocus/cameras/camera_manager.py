# -*- coding: utf-8 -*-

from importlib.util import spec_from_file_location, module_from_spec
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class CameraPluginManager:

    def __init__(self, path: Path) -> None:
        self.plugins: list = []
        self.path: Path = path

    def load_metadata(self):
        json_file = self.path / "extensions.json"
        with json_file.open() as file:
            plugin_data = json.load(file)
        logger.info(f"Found available plugins for the system: {plugin_data['plugins']}")
        return plugin_data["plugins"]

    def load_plugin(self, plugin_path: Path):
        spec = spec_from_file_location(plugin_path.name, plugin_path)
        module = module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def discover_plugins(self):
        if self.plugins:
            self.plugins.clear()
        for file in self.path.iterdir():
            if file.is_file() and file.name.endswith(".py"):
                module_path: Path = file
                plugin = self.load_plugin(module_path)
                self.plugins.append(plugin)
        return self.plugins
