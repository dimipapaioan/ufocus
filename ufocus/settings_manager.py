# -*- coding: utf-8 -*-

import json
import logging
from threading import Lock

from PySide6.QtCore import QPoint

from dirs import BASE_PATH

DEFAULT_SETTINGS = {
    "spinboxImagesToAccumulate": 30,
    "spinboxThreshold": -1,
    "spinboxGaussianKernel": 11,
    "spinboxInitialPS1": 0.0,
    "spinboxInitialPS2": 0.0,
    "spinboxXATol": -2,
    "spinboxFATol": 6,
    "spinboxMaxIter": 100,
    "spinboxMaxFEval": 100,
    "p_i": None,
    "p_f": None,
    "roi": False,
    "roi_draw": True,
    "p_cross_x40": None,
    "p_cross_x16": None,
    "draw_crosshair_x40": False,
    "draw_crosshair_x16": False,
    "pts_scan_x40": [],
    "pts_scan_x16": [],
    "draw_scan_x40": False,
    "draw_scan_x16": False,
}

SETTINGS_T1 = (
    "p_i",
    "p_f",
    "roi",
    "roi_draw",
    "p_cross_x40",
    "p_cross_x16",
    "draw_crosshair_x40",
    "draw_crosshair_x16",
    "pts_scan_x40",
    "pts_scan_x16",
    "draw_scan_x40",
    "draw_scan_x16",
)

logger = logging.getLogger(__name__)


class JSONSpecialEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, QPoint):
            return {"__class__": "QPoint", "x": obj.x(), "y": obj.y()}
        return super().default(obj)


class JSONSpecialDecoder(json.JSONDecoder):
    def __init__(self):
        super().__init__(object_hook=self.custom_decoder)

    def custom_decoder(self, obj):
        if obj.get("__class__") == "QPoint":
            return QPoint(obj["x"], obj["y"])
        return obj


class SettingsManagerMeta(type):
    """
    Thread-safe implementation of a Singleton for the SettingsManager.
    """

    _instance = None
    _lock: Lock = Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                instance = super().__call__(*args, **kwargs)
                cls._instance = instance
        return cls._instance


class SettingsManager(metaclass=SettingsManagerMeta):
    """Create a thread-safe settings manager singleton for the application."""

    def __init__(self, parent):
        self.parent = parent
        self.user_settings = self.loadUserSettings()

    def setDefaultValues(self):
        for key, value in DEFAULT_SETTINGS.items():
            if key in SETTINGS_T1:
                setattr(self.parent.video_label, key, value)
            else:
                atr = getattr(self.parent, key)
                atr.setValue(value)
        self.user_settings.update(DEFAULT_SETTINGS)
        self.saveUserSettings()

    def loadUserSettings(self):
        if BASE_PATH / "user_settings.json" in BASE_PATH.glob("*.json"):
            logger.info("Found existing user settings")
            with open(f"{BASE_PATH}/user_settings.json", "r") as file:
                user_settings = json.load(file, cls=JSONSpecialDecoder)
            return user_settings
        else:
            logger.info("Using the default settings")
            with open(f"{BASE_PATH}/user_settings.json", "w") as file:
                json.dump(DEFAULT_SETTINGS, file, cls=JSONSpecialEncoder)
            return DEFAULT_SETTINGS.copy()

    def setUserValues(self):
        if self.user_settings is not None:
            for key, value in self.user_settings.items():
                if key in SETTINGS_T1:
                    setattr(self.parent.video_label, key, value)
                else:
                    atr = getattr(self.parent, key)
                    atr.setValue(value)
        else:
            self.setDefaultValues()

    def saveUserSettings(self):
        with open(f"{BASE_PATH}/user_settings.json", "w") as file:
            json.dump(self.user_settings, file, cls=JSONSpecialEncoder)
