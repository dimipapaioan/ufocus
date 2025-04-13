import csv
import time
from dataclasses import dataclass, field, fields
from datetime import date
from itertools import zip_longest
from math import nan

import PySide6QtAds as QtAds
from pyqtgraph import PlotWidget, getConfigOption, mkBrush, mkPen
from PySide6.QtCore import QSize, Slot
from PySide6.QtGui import QAction, QIcon, QPixmap
from PySide6.QtWidgets import (
    QMessageBox,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

import resources  # noqa: F401
from dirs import BASE_DATA_PATH
from image_processing.image_processing import DetectedEllipse
from widgets.floating_widget import FloatingWidget


@dataclass
class RunData:
    x_c: list[float] = field(default_factory=list)
    y_c: list[float] = field(default_factory=list)
    minor: list[float] = field(default_factory=list)
    major: list[float] = field(default_factory=list)
    angle: list[float] = field(default_factory=list)
    area: list[float] = field(default_factory=list)
    perimeter: list[float] = field(default_factory=list)
    circularity: list[float] = field(default_factory=list)
    eccentricity: list[float] = field(default_factory=list)
    current1: list[float] = field(default_factory=list)
    current2: list[float] = field(default_factory=list)
    cost_func: list[float] = field(default_factory=list)

    def append_data(self, data: DetectedEllipse) -> None:
        for f in fields(data):
            getattr(self, f.name).append(getattr(data, f.name))

    def clear_data(self) -> None:
        for f in fields(self):
            getattr(self, f.name).clear()


class PlottingWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.data = RunData()
        legend_pen = getConfigOption("foreground")
        legend_brush = getConfigOption("background")

        QtAds.CDockManager.setConfigFlags(QtAds.CDockManager.DefaultNonOpaqueConfig)
        QtAds.CDockManager.setConfigFlag(
            QtAds.CDockManager.RetainTabSizeWhenCloseButtonHidden, True
        )
        QtAds.CDockManager.setAutoHideConfigFlags(
            QtAds.CDockManager.DefaultAutoHideConfig
        )
        # QtAds.CDockManager.setAutoHideConfigFlag(QtAds.CDockManager.AutoHideShowOnMouseOver, True)
        manager = QtAds.CDockManager()

        self.pw1 = PlotWidget()
        self.graph1 = self.pw1.getPlotItem()
        self.graph1.showAxes(True)
        self.graph1.setTitle("Ellipse Axes")
        self.graph1.setLabels(left="Length [px]", bottom="Count")
        self.graph1.addLegend(pen=legend_pen, brush=legend_brush, labelTextSize="8pt", colCount=2)
        self.item1 = self.graph1.plot(
            self.data.major,
            pen=mkPen({"color": "#1f77b4", "width": 2}),
            symbol="o",
            symbolPen=mkPen({"color": "#1f77b4", "width": 1}),
            symbolBrush=mkBrush("#1f77b4"),
            symbolSize=5,
            name="Major",
        )
        self.item2 = self.graph1.plot(
            self.data.minor,
            pen=mkPen({"color": "#ff7f0e", "width": 2}),
            symbol="o",
            symbolPen=mkPen({"color": "#ff7f0e", "width": 1}),
            symbolBrush=mkBrush("#ff7f0e"),
            symbolSize=5,
            name="Minor",
        )
        # self.grid = pg.GridItem(pen='k', textPen=None)
        # self.grid.setTickSpacing(x=[1.0, None], y=[1.0, None])
        # self.graph.addItem(self.grid)
        # self.graph.showGrid(x=True, y=True)

        self.dock_widget1 = QtAds.CDockWidget("Ellipse Axes")
        self.dock_widget1.setContentsMargins(5, 5, 10, 5)
        self.dock_widget1.setWidget(self.pw1)
        manager.addDockWidget(QtAds.LeftDockWidgetArea, self.dock_widget1)

        self.pw2 = PlotWidget()
        self.graph2 = self.pw2.getPlotItem()
        self.graph2.showAxes(True)
        self.graph2.setTitle("Quadrupole Currents")
        self.graph2.setLabels(left="Current [A]", bottom="Count")
        self.graph2.addLegend(pen=legend_pen, brush=legend_brush, labelTextSize="8pt", colCount=2)
        self.item3 = self.graph2.plot(
            self.data.current1,
            pen=mkPen({"color": "#1f77b4", "width": 2}),
            symbol="o",
            symbolPen=mkPen({"color": "#1f77b4", "width": 1}),
            symbolBrush=mkBrush("#1f77b4"),
            symbolSize=5,
            name="PS1",
        )
        self.item4 = self.graph2.plot(
            self.data.current2,
            pen=mkPen({"color": "#ff7f0e", "width": 2}),
            symbol="o",
            symbolPen=mkPen({"color": "#ff7f0e", "width": 1}),
            symbolBrush=mkBrush("#ff7f0e"),
            symbolSize=5,
            name="PS2",
        )
        # self.grid = pg.GridItem(pen='k', textPen=None)
        # self.grid.setTickSpacing(x=[1.0, None], y=[1.0, None])
        # self.graph.addItem(self.grid)
        # self.graph.showGrid(x=True, y=True)
        # self.graph1.scene().sigMouseClicked.connect(self.onMouseHovered)
        # self.graph2.scene().sigMouseClicked.connect(self.onMouseHovered)

        self.dock_widget2 = QtAds.CDockWidget("Currents")
        self.dock_widget2.setContentsMargins(5, 5, 10, 5)
        self.dock_widget2.setWidget(self.pw2)
        manager.addDockWidget(QtAds.RightDockWidgetArea, self.dock_widget2)

        self.pw3 = PlotWidget()
        self.graph3 = self.pw3.getPlotItem()
        self.graph3.showAxes(True)
        self.graph3.setTitle("Minimization Function")
        self.graph3.setLabels(left="Value [px⁴]", bottom="Count")
        self.graph3.getAxis("left").enableAutoSIPrefix(False)
        self.graph3.setLogMode(x=False, y=True)
        # self.graph3.addLegend(pen='k', labelTextSize='10pt')
        self.item5 = self.graph3.plot(
            self.data.cost_func,
            pen=mkPen({"color": "#1f77b4", "width": 2}),
            symbol="o",
            symbolPen=mkPen({"color": "#1f77b4", "width": 1}),
            symbolBrush=mkBrush("#1f77b4"),
            symbolSize=5,
            name="MinFunc",
        )

        self.dock_widget3 = QtAds.CDockWidget("Min Function")
        self.dock_widget3.setContentsMargins(5, 5, 10, 5)
        self.dock_widget3.setWidget(self.pw3)
        manager.addDockWidget(QtAds.BottomDockWidgetArea, self.dock_widget3)

        # self.dock_widget4 = QtAds.CDockWidget("Plot 4")
        # self.dock_widget4.setWidget(QWidget())
        # manager.addDockWidget(QtAds.BottomDockWidgetArea, self.dock_widget4, h)

        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(16, 16))
        self.actionOpenInWindow = QAction("Open in window", self)
        self.actionOpenInWindow.setIcon(
            QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg"))
        )
        self.actionOpenInWindow.setCheckable(True)
        self.actionOpenInWindow.triggered.connect(self.onActionOpenWindowClicked)

        self.actionSaveData = QAction("Save all data", self)
        self.actionSaveData.setIcon(QIcon(QPixmap(":/icons/floppy-disk-solid.svg")))
        self.actionSaveData.triggered.connect(self.onActionSaveData)

        self.actionClearData = QAction("Clear all data", self)
        self.actionClearData.setIcon(QIcon(QPixmap(":/icons/trash-can-solid.svg")))
        self.actionClearData.triggered.connect(self.onActionClearData)

        # Add actions to toolbar
        self.toolbar.addAction(self.actionOpenInWindow)
        self.toolbar.addAction(self.actionSaveData)
        self.toolbar.addAction(self.actionClearData)

        # plotslayout = QHBoxLayout()
        # plotslayout.addWidget(self.pw1)
        # plotslayout.addWidget(self.pw2)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(manager)

        self.setLayout(layout)

    @Slot(DetectedEllipse)
    def updatePlotEllipseAxes(self, detected_ellipse: DetectedEllipse) -> None:
        self.data.append_data(detected_ellipse)
        self.item1.setData(self.data.major)
        self.item2.setData(self.data.minor)

    @Slot(list)
    def updatePlotCurrents(self, x) -> None:
        self.data.current1.append(x[0])
        self.data.current2.append(x[1])

        self.item3.setData(self.data.current1)
        self.item4.setData(self.data.current2)

    @Slot(float)
    def updatePlotFunction(self, v) -> None:
        self.data.cost_func.append(v)
        self.item5.setData(self.data.cost_func)

    @Slot()
    def onActionOpenWindowClicked(self, checked) -> None:
        if checked:
            self.plottingWindow = FloatingWidget("Plotting", self)
            self.actionOpenInWindow.setIcon(
                QIcon(QPixmap(":/icons/arrow-right-to-bracket-solid.svg"))
            )
            self.actionOpenInWindow.setText("Return to main window")
        else:
            self.actionOpenInWindow.setIcon(
                QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg"))
            )
            self.plottingWindow.close()
            self.actionOpenInWindow.setText("Open in window")
            self.plottingWindow = None

    @Slot()
    def onActionSaveData(self, path=None) -> None:
        if not path or not path.exists():
            path = BASE_DATA_PATH / date.today().isoformat()
            path.mkdir(parents=True, exist_ok=True)
        filename = path / f"data_{date.today()}_{time.time_ns()}.csv"
        with filename.open(mode="w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(
                ["Count", "xc", "yc", "minor", "major", "angle", "Q1", "Q2", "Function"]
            )
            for row, line in enumerate(
                zip_longest(
                    self.data.x_c,
                    self.data.y_c,
                    self.data.minor,
                    self.data.major,
                    self.data.angle,
                    self.data.current1,
                    self.data.current2,
                    self.data.cost_func,
                    fillvalue=nan,
                )
            ):
                writer.writerow([row, *line])

        QMessageBox.information(
            self,
            "Data saved",
            f"Data were successfully saved to {filename}.",
            QMessageBox.StandardButton.Ok,
        )

    @Slot()
    def onActionClearData(self) -> None:
        self.data.clear_data()

        self.item1.setData(self.data.major)
        self.item2.setData(self.data.minor)
        self.item3.setData(self.data.current1)
        self.item4.setData(self.data.current2)
        self.item5.setData(self.data.cost_func)
