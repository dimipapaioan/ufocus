import PySide6QtAds as QtAds
from numpy import ndarray
from pyqtgraph import PlotWidget, mkPen
from PySide6.QtCore import QSize, Slot
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from . import resources  # noqa: F401
from .floating_widget import FloatingWidget


class HistogramsWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.hor_data = []
        self.vert_data = []
        self.hist_data = []

        manager = QtAds.CDockManager()

        self.pw1 = PlotWidget()
        self.graph1 = self.pw1.getPlotItem()
        self.graph1.showAxes(True)
        self.graph1.setTitle("Y Profile")
        self.graph1.setLabels(left="Normalized Intensity", bottom="Pixel Y")
        self.item1 = self.graph1.plot(
            self.hor_data,
            stepMode="center",
            fillLevel=0,
            fillOutline=True,
            pen=mkPen({"color": "#1f77b4"}),
            # fillBrush=pg.mkBrush("#1f77b4"),
            name="y_profile",
        )

        self.dock_widget1 = QtAds.CDockWidget("Y Profile")
        self.dock_widget1.setContentsMargins(5, 5, 10, 5)
        self.dock_widget1.setWidget(self.pw1)
        manager.addDockWidget(QtAds.LeftDockWidgetArea, self.dock_widget1)

        self.pw2 = PlotWidget()
        self.graph2 = self.pw2.getPlotItem()
        self.graph2.showAxes(True)
        self.graph2.setTitle("X Profile")
        self.graph2.setLabels(left="Normalized Intensity", bottom="Pixel X")
        self.item2 = self.graph2.plot(
            self.vert_data,
            stepMode="center",
            fillLevel=0,
            # fillOutline=True,
            pen=mkPen({"color": "#1f77b4"}),
            # fillBrush=pg.mkBrush("#1f77b4"),
            name="x_profile",
        )

        self.dock_widget2 = QtAds.CDockWidget("X Profile")
        self.dock_widget2.setContentsMargins(5, 5, 10, 5)
        self.dock_widget2.setWidget(self.pw2)
        manager.addDockWidget(QtAds.RightDockWidgetArea, self.dock_widget2)

        self.pw3 = PlotWidget()
        self.graph3 = self.pw3.getPlotItem()
        self.graph3.showAxes(True)
        self.graph3.setTitle("ROI Histogram")
        self.graph3.setLabels(left="Counts", bottom="Intensity")
        self.graph3.setLogMode(x=False, y=True)
        self.item3 = self.graph3.plot(
            self.hist_data,
            stepMode="center",
            fillLevel=0,
            # fillOutline=True,
            pen=mkPen({"color": "#1f77b4"}),
            # fillBrush=pg.mkBrush("#1f77b4"),
            name="hist",
        )

        self.dock_widget3 = QtAds.CDockWidget("ROI Histogram")
        self.dock_widget3.setContentsMargins(5, 5, 10, 5)
        self.dock_widget3.setWidget(self.pw3)
        manager.addDockWidget(QtAds.BottomDockWidgetArea, self.dock_widget3)

        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(16, 16))
        self.actionOpenInWindow = QAction("Open in window", self)
        self.actionOpenInWindow.setIcon(
            QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg"))
        )
        self.actionOpenInWindow.setCheckable(True)
        self.actionOpenInWindow.triggered.connect(self.onActionOpenWindowClicked)

        self.actionClearData = QAction("Clear all data", self)
        self.actionClearData.setIcon(QIcon(QPixmap(":/icons/trash-can-solid.svg")))
        self.actionClearData.triggered.connect(self.onActionClearData)

        # Add actions to toolbar
        self.toolbar.addAction(self.actionOpenInWindow)
        self.toolbar.addAction(self.actionClearData)

        # plotslayout = QHBoxLayout()
        # plotslayout.addWidget(self.pw1)
        # plotslayout.addWidget(self.pw2)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(manager)

        self.setLayout(layout)

    @Slot(ndarray)
    def updateHistHor(self, h) -> None:
        self.hor_data = h
        self.item1.setData(range(len(self.hor_data) + 1), self.hor_data)

    @Slot(ndarray)
    def updateHistVert(self, v) -> None:
        self.vert_data = v
        self.item2.setData(range(len(self.vert_data) + 1), self.vert_data)

    @Slot(ndarray)
    def updateHist(self, v) -> None:
        self.hist_data = v
        self.item3.setData(range(len(self.hist_data) + 1), self.hist_data)

    @Slot()
    def onActionOpenWindowClicked(self, checked) -> None:
        if checked:
            self.histogramsWindow = FloatingWidget("Histograms", self)
            self.actionOpenInWindow.setIcon(
                QIcon(QPixmap(":/icons/arrow-right-to-bracket-solid.svg"))
            )
            self.actionOpenInWindow.setText("Return to main window")
        else:
            self.actionOpenInWindow.setIcon(
                QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg"))
            )
            self.histogramsWindow.close()
            self.actionOpenInWindow.setText("Open in window")
            self.histogramsWindow = None

    @Slot()
    def onActionClearData(self) -> None:
        self.hor_data = []
        self.vert_data = []
        self.hist_data = []

        self.item1.setData(self.hor_data)
        self.item2.setData(self.vert_data)
        self.item3.setData(self.hist_data)
