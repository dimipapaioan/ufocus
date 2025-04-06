from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QWidget

import resources  # noqa: F401


class FullScreenWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)

        self.parentLayout = self.parentWidget().liveFeed.layout()
        self.setLayout(self.parentLayout)
        self.setScreen(self.parentWidget().screen())
        self.setWindowFlags(Qt.WindowType.Window)
        self.showFullScreen()

        self.shortcutExitFullScreen = QShortcut(QKeySequence("Escape"), self)
        self.shortcutExitFullScreen.activated.connect(
            self.parentWidget().actionOpenInFullScreen.trigger
        )
