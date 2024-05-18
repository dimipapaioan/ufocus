# -*- coding: utf-8 -*-

from cameras.camera_base import CameraBase


class BuiltInCamera(CameraBase):

    def __init__(self):
        super().__init__()

    def connect(self):
        pass

    def disconnect(self):
        pass

    def start(self):
        pass

    def stop(self):
        pass
