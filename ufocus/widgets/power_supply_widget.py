from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QSizePolicy,
    QLCDNumber,
    QPushButton,
    QGroupBox,
    QGridLayout,
    QFrame,
    QDial,
    QDoubleSpinBox,
)


class PowerSupplyWidget(QWidget):
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.voltageLCD = QLCDNumber(7)
        self.voltageLCD.display("  OFF  ")
        self.voltageLCD.setSegmentStyle(QLCDNumber.Flat)
        # self.voltageLCD.setMinimumHeight(70)
        self.voltageLCD.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding
        )
        # self.voltageLCD.setFrameStyle(QFrame.NoFrame)
        self.voltageLCD.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)

        self.currentLCD = QLCDNumber(7)
        self.currentLCD.display("  OFF  ")
        self.currentLCD.setSegmentStyle(QLCDNumber.Flat)
        # self.currentLCD.setMinimumHeight(70)
        self.currentLCD.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding
        )
        # self.currentLCD.setFrameStyle(QFrame.NoFrame)
        self.currentLCD.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)

        self.voltageDial = QDial()
        self.voltageDial.installEventFilter(self)
        self.voltageDial.setRange(0, 60_000)
        self.voltageDial.setSingleStep(10)
        self.voltageDial.setPageStep(25)
        self.voltageDial.setNotchTarget(2.0)
        self.voltageDial.setNotchesVisible(True)
        self.voltageDial.setCursor(Qt.CursorShape.SizeAllCursor)
        # self.voltageDial.setTracking(False)
        self.voltageDial.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding
        )
        # self.voltageDial.setValue(40)
        # self.voltageDial.valueChanged.connect(self.sliderVoltageMoved)

        self.spinboxVoltage = QDoubleSpinBox()
        self.spinboxVoltage.setRange(0.0, 6.0)
        self.spinboxVoltage.setDecimals(4)
        self.spinboxVoltage.clear()

        self.buttonVoltage = QPushButton("Set")
        self.buttonVoltage.setCursor(Qt.CursorShape.PointingHandCursor)
        self.buttonVoltage.clicked.connect(self.voltageSetManually)

        self.currentDial = QDial()
        self.currentDial.installEventFilter(self)
        self.currentDial.setRange(0, 10_000)
        self.currentDial.setSingleStep(1)
        self.currentDial.setPageStep(10)
        self.currentDial.setNotchTarget(20.7)
        self.currentDial.setNotchesVisible(True)
        self.currentDial.setCursor(Qt.CursorShape.SizeAllCursor)
        # self.currentDial.setTracking(False)
        self.currentDial.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding
        )
        # self.currentDial.setValue(40)
        # self.currentDial.valueChanged.connect(self.sliderCurrentMoved)
        # self.currentDial.actionTriggered.connect(self.onActionTriggered)
        self.currentDial.valueChanged.connect(
            lambda value: self.spinboxCurrent.setValue(value / 100)
        )

        self.spinboxCurrent = QDoubleSpinBox()
        self.spinboxCurrent.setRange(0.0, 100.0)
        self.spinboxCurrent.clear()

        self.buttonCurrent = QPushButton("Set")
        self.buttonCurrent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.buttonCurrent.clicked.connect(self.currentSetManually)

        displayLayout = QGridLayout()
        displayLayout.addWidget(
            QLabel("Voltage"), 0, 0, 1, 2, Qt.AlignmentFlag.AlignHCenter
        )
        displayLayout.addWidget(self.voltageLCD, 1, 0, 1, 2)
        displayLayout.addWidget(self.voltageDial, 2, 0, 1, 2)
        displayLayout.addWidget(self.buttonVoltage, 3, 0, 1, 1)
        displayLayout.addWidget(self.spinboxVoltage, 3, 1, 1, 1)

        displayLayout.addWidget(
            QLabel("Current"), 0, 2, 1, 2, Qt.AlignmentFlag.AlignHCenter
        )
        displayLayout.addWidget(self.currentLCD, 1, 2, 1, 2)
        displayLayout.addWidget(self.currentDial, 2, 2, 1, 2)
        displayLayout.addWidget(self.buttonCurrent, 3, 2, 1, 1)
        displayLayout.addWidget(self.spinboxCurrent, 3, 3, 1, 1)

        groupLCD = QGroupBox()
        if title:
            groupLCD.setTitle(title)
        groupLCD.setLayout(displayLayout)

        layout = QGridLayout()
        layout.addWidget(groupLCD, 0, 0)
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

    @Slot()
    def sliderCurrentMoved(self):
        self.currentLCD.display(f"{self.currentDial.value() / 100:4.2f}")

    @Slot()
    def currentSetManually(self):
        v = self.spinboxCurrent.value()
        # print(v)
        v_int = int(v * 100)
        # print(v_int)
        self.currentDial.setValue(v_int)

    @Slot()
    def sliderVoltageMoved(self):
        self.voltageLCD.display(f"{self.voltageDial.value() / 10_000:.4f}")

    @Slot()
    def voltageSetManually(self):
        v = self.spinboxVoltage.value()
        # print(v)
        v_int = int(v * 10000)
        # print(v_int)
        self.voltageDial.setValue(v_int)

    def eventFilter(self, source, event):
        if isinstance(source, QDial) and isinstance(event, QMouseEvent):
            # event.ignore()
            return True

        return super().eventFilter(source, event)


if __name__ == "__main__":
    import sys

    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)

    window = PowerSupplyWidget()
    window.show()

    sys.exit(app.exec())
