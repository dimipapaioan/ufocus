# -*- coding: utf-8 -*-
import logging
from typing import Optional

from cv2 import VideoCapture, error

from cameras.camera_base import CameraBase
from workers.builtin_camera_worker import BuiltInCameraWorker

logger = logging.getLogger(__name__)


class CameraConnectionError(Exception):
    pass


class BuiltInCamera(CameraBase):

    def __init__(self):
        super().__init__()
        self.camera: Optional[VideoCapture] = None

    def configure(self) -> None:
        self.width = 640
        self.height = 480

    def connect(self, idx: int) -> None:
        self.camera = VideoCapture()
        self.camera.setExceptionMode(True)
        try:
            self.camera.open(0)
        except error as e:
            logger.error(e.msg)
            raise CameraConnectionError from e
        else:
            self.is_connected = True

    def disconnect(self) -> None:
        self.stop()
        self.camera = None
        self.is_connected = False

    def get_worker(self, parent):
        return BuiltInCameraWorker(self.camera, parent)

    def start(self):
        pass

    def stop(self) -> None:
        if self.camera.isOpened():
            self.camera.release()
