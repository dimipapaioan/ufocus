# -*- coding: utf-8 -*-

import logging
from typing import Optional

from pypylon import pylon

from cameras.camera_base import CameraBase
from workers.basler_camera_worker import BaslerCameraWorker

logger = logging.getLogger(__name__)


class CameraConnectionError(Exception):
    pass


class BaslerCamera(CameraBase):

    def __init__(self):
        super().__init__()
        self.factory: pylon.TlFactory = pylon.TlFactory.GetInstance()
        self.devices = self.list_cameras()
        self.camera: Optional[pylon.InstantCamera] = None

    def list_cameras(self) -> tuple:
        devices: tuple = self.factory.EnumerateDevices()
        if devices:
            logger.info("Camera devices found")
        else:
            logger.warning("No camera devices found")
        return devices

    def configure(self) -> None:
        self.camera.PixelFormat.SetValue("Mono8")
        self.width = self.camera.Width.GetValue()
        self.height = self.camera.Height.GetValue()

    def reset(self) -> None:
        if self.camera.IsOpen():
            if self.camera.IsGrabbing():
                self.camera.StopGrabbing()

            # Retrieve default settings
            self.camera.UserSetSelector.SetValue("Default")
            self.camera.UserSetLoad.Execute()

            # Re-configure the camera
            self.configure()

    def connect(self, idx: int = 0) -> None:
        try:
            self.camera = pylon.InstantCamera(
                self.factory.CreateDevice(self.devices[idx])
            )
            self.camera.Open()
        except pylon.RuntimeException:
            raise CameraConnectionError

    def disconnect(self) -> None:
        if self.camera.IsGrabbing():
            self.camera.StopGrabbing()

        self.camera.Close()
        self.camera.DestroyDevice()

    def get_worker(self, parent):
        return BaslerCameraWorker(self.camera, parent)

    def start(self):
        pass

    def stop(self):
        pass
