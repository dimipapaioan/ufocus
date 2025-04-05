# -*- coding: utf-8 -*-

from abc import ABC, abstractmethod
from typing import Optional

from ..workers.camera_worker_base import CameraWorker


class Camera(ABC):

    def __init__(self) -> None:
        super().__init__()
        self.camera = None
        self.width: Optional[int] = None
        self.height: Optional[int] = None
        self.is_connected: bool = False

    @abstractmethod
    def configure(self): ...

    @abstractmethod
    def reset(self): ...

    @abstractmethod
    def connect(self): ...

    @abstractmethod
    def disconnect(self): ...

    @abstractmethod
    def get_worker(self) -> CameraWorker: ...

    @abstractmethod
    def start(self): ...

    @abstractmethod
    def stop(self): ...
