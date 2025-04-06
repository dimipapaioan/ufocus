# -*- coding: utf-8 -*-

import logging
import time

from numpy import ndarray
from pypylon import pylon
from pypylon.genicam import GenericException
from PySide6.QtCore import QObject, Signal, Slot
from PySide6.QtGui import QImage

from workers.camera_worker_base import CameraWorker

logger = logging.getLogger(__name__)


class BaslerCameraWorker(CameraWorker):

    def __init__(self, camera: pylon.InstantCamera, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.camera = camera
        self.handler = CameraImageHandler(self.parent)
        self.camera.RegisterImageEventHandler(self.handler, pylon.RegistrationMode_ReplaceAll, pylon.Cleanup_Delete)
        self.printer = ConfigurationEventPrinter()
        self.camera.RegisterConfiguration(self.printer, pylon.RegistrationMode_Append, pylon.Cleanup_Delete)
        self.handler.updateFrame.connect(self.signals.updateFrame.emit)
        self.handler.progress.connect(self.signals.progress.emit)

        logger.info("Camera worker initialized")

    @Slot()
    def run(self):
        try:
            self.camera.StartGrabbing(pylon.GrabStrategy_OneByOne, pylon.GrabLoop_ProvidedByInstantCamera)
            logger.info("Camera worker started")
        except GenericException as e:
            logger.error(e)
            self.signals.error.emit()
        else:
            while self.camera.IsGrabbing():
                self.signals.fps.emit(self.camera.ResultingFrameRate.GetValue())
                time.sleep(0.33)
            self.camera.DeregisterImageEventHandler(self.handler)
            self.camera.DeregisterConfiguration(self.printer)
        finally:
            logger.info("Camera worker finished")
            self.signals.finished.emit()


class CameraImageHandler(pylon.ImageEventHandler, QObject):
    progress = Signal(ndarray)
    updateFrame = Signal(QImage)
    
    def __init__(self, parent=None):
        super().__init__()
        super(pylon.ImageEventHandler, self).__init__(parent)
        # self.parent = parent
        # self.camera = camera
        # self.img = np.zeros((self.camera.Height.Value, self.camera.Width.Value))
        # self.img = np.zeros((2048, 2448))

    def OnImageGrabbed(self, camera, grab):
        if grab.GrabSucceeded():
            self.img: ndarray = grab.GetArray()
            self.progress.emit(self.img)
            if self.img.ndim == 2:
                h, w = self.img.shape
                image = QImage(self.img.data, w, h, w, QImage.Format.Format_Grayscale8)
            elif self.img.ndim == 3:
                h, w, ch = self.img.shape
                image = QImage(self.img.data, w, h, ch * w, QImage.Format.Format_RGB888)
            # self.image = self.image.scaled(320, 240, Qt.KeepAspectRatio)
            self.updateFrame.emit(image)
        

    def OnImagesSkipped(self, camera, countOfSkippedImages):
        logger.warning(f"Camera skipped {countOfSkippedImages} images")
        
class ConfigurationEventPrinter(pylon.ConfigurationEventHandler):
    def OnAttach(self):
        logger.debug("OnAttach event")

    def OnAttached(self, camera):
        logger.debug(f"OnAttached event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnOpen(self, camera):
        logger.debug(f"OnOpen event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnOpened(self, camera):
        logger.debug(f"OnOpened event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnGrabStart(self, camera):
        logger.debug(f"OnGrabStart event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnGrabStarted(self, camera):
        logger.debug(f"OnGrabStarted event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnGrabStop(self, camera):
        logger.debug(f"OnGrabStop event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnGrabStopped(self, camera):
        logger.debug(f"OnGrabStopped event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnClose(self, camera):
        logger.debug(f"OnClose event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnClosed(self, camera):
        logger.debug(f"OnClosed event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnDestroy(self, camera):
        logger.debug(f"OnDestroy event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnDestroyed(self, camera):
        logger.debug("OnDestroyed event")

    def OnDetach(self, camera):
        logger.debug(f"OnDetach event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnDetached(self, camera):
        logger.debug(f"OnDetached event for device {camera.GetDeviceInfo().GetModelName()}")

    def OnGrabError(self, camera, errorMessage):
        logger.error(f"OnGrabError event for device {camera.GetDeviceInfo().GetModelName()}: {errorMessage}")

    def OnCameraDeviceRemoved(self, camera):
        logger.debug(f"OnCameraDeviceRemoved event for device {camera.GetDeviceInfo().GetModelName()}")
