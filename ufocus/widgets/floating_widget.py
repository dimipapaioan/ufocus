from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

from . import resources  # noqa: F401


class FloatingWidget(QWidget):
    def __init__(self, title: str, widget: QWidget, parent=None) -> None:
        super().__init__(widget)
        self.title = title
        self.widget = widget

        self.parentLayout = self.widget.layout()
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setLayout(self.parentLayout)
        self.show()

    def closeEvent(self, event) -> None:
        if self.widget.actionOpenInWindow.isChecked():
            self.widget.actionOpenInWindow.trigger()
        self.widget.setLayout(self.parentLayout)

        return super().closeEvent(event)
