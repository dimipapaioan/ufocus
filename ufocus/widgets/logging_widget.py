import logging

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogSignals(QObject):
    message = Signal(str, logging.LogRecord)


class LoggerWidgetHandler(logging.Handler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.signals = LogSignals()

    def emit(self, record) -> None:
        msg = self.format(record)
        self.signals.message.emit(msg, record)


class LoggerWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # self.colors = {
        #     logging.DEBUG: 'black',
        #     logging.INFO: 'blue',
        #     logging.WARNING: 'orange',
        #     logging.ERROR: 'red',
        #     logging.CRITICAL: 'purple',
        # }

        self.log_output = QPlainTextEdit()
        self.log_output.setReadOnly(True)
        # self.log_output.setFrameStyle(0)
        self.log_output.setMaximumBlockCount(2000)

        font = QFont("nosuchfont")
        font.setStyleHint(font.StyleHint.Monospace)
        font.setPointSize(10)
        self.log_output.setFont(font)

        self.handler = LoggerWidgetHandler()
        self.handler.setFormatter(
            logging.Formatter("%(asctime)s | %(levelname)-7s | %(name)s: %(message)s")
        )

        self.handler.signals.message.connect(self.update_logger)

        layout = QVBoxLayout()
        layout.addWidget(self.log_output)
        self.setLayout(layout)

    @Slot(str, logging.LogRecord)
    def update_logger(self, status: str, record: logging.LogRecord) -> None:
        # color = self.colors.get(record.levelno, 'black')
        # s = '<pre><font color="%s">%s</font></pre>' % (color, status)
        # self.log_output.appendHtml(s)
        self.log_output.appendPlainText(status)
