# -*- coding: utf-8 -*-

import logging
from typing import Optional

from pypylon import pylon

from cameras.camera_base import Camera
from cameras.exceptions import CameraConnectionError
from workers.basler_camera_worker import BaslerCameraWorker

logger = logging.getLogger(__name__)


class BaslerCamera(Camera):

    def __init__(self):
        super().__init__()
        self.factory: pylon.TlFactory = pylon.TlFactory.GetInstance()
        self.devices = self.factory.EnumerateDevices()
        self.camera: Optional[pylon.InstantCamera] = None

    def configure(self) -> None:
        self.camera.PixelFormat.SetValue("Mono8")
        self.width = self.camera.Width.GetValue()
        self.height = self.camera.Height.GetValue()

    def reset(self) -> None:
        if self.camera.IsOpen():
            self.stop()

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
        except (pylon.RuntimeException, IndexError):
            raise CameraConnectionError
        else:
            self.is_connected = True

    def disconnect(self) -> None:
        self.stop()
        self.camera.Close()
        self.camera.DestroyDevice()
        self.is_connected = False

    def get_worker(self, parent) -> BaslerCameraWorker:
        return BaslerCameraWorker(self.camera, parent)

    def start(self):
        pass

    def stop(self) -> None:
        if self.camera.IsGrabbing():
            self.camera.StopGrabbing()
