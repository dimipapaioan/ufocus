# -*- coding: utf-8 -*-

import logging
import time

import cv2
from numpy import ndarray
from PySide6.QtCore import Slot
from PySide6.QtGui import QImage

from workers.camera_worker_base import CameraWorker

logger = logging.getLogger(__name__)


# Create a camera worker class
class BuiltInCameraWorker(CameraWorker):
    def __init__(self, camera, parent=None):
        super().__init__(parent)
        self.camera: cv2.VideoCapture = camera

    @Slot()
    def run(self):
        try:
            self.camera.open(0)
        except Exception as e:
            logger.error(e)
            self.signals.error.emit()
        else:
            frames = 0
            while self.camera.isOpened():
                if frames == 0:
                    start = time.perf_counter()
                try:
                    ret, frame = self.camera.read()
                except cv2.error:
                    pass
                else:
                    if ret:
                        # Reading the image in RGB to display it
                        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        self.signals.progress.emit(img)

                        if img.ndim == 2:
                            h, w = img.shape
                            img = QImage(
                                image.data, w, h, w, QImage.Format.Format_Grayscale8
                            )
                        elif img.ndim == 3:
                            h, w, ch = img.shape
                        image = QImage(img.data, w, h, ch * w, QImage.Format.Format_RGB888)
                        self.signals.updateFrame.emit(image)
                        frames += 1
                        if frames == 30:
                            self.signals.fps.emit(frames / (time.perf_counter() - start))
                            frames = 0
        finally:
            logger.info("Camera worker finished")
            self.signals.finished.emit()
