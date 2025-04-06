from numpy import ndarray
from PySide6.QtCore import QObject, QRunnable, Signal
from PySide6.QtGui import QImage


class CameraWorkerSignals(QObject):
    progress = Signal(ndarray)
    updateFrame = Signal(QImage)
    fps = Signal(float)
    error = Signal()
    finished = Signal()


class CameraWorker(QRunnable):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.signals = CameraWorkerSignals(parent)
        self.manually_terminated = False
