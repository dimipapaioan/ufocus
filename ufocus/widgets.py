# -*- coding: utf-8 -*-

import csv
import logging
import time
from dataclasses import dataclass, field, fields
from datetime import date
from itertools import zip_longest
from math import dist, nan

import cv2
from numpy import ndarray
from PySide6.QtCore import (
    Qt, Signal, Slot, QSize, QRectF, QPoint, QObject
)
from PySide6.QtGui import (
    QImage, QColor, QPixmap, QPainter, QMouseEvent, QPen,
    QAction, QIcon, QShortcut, QKeySequence, QPolygon, QFont
)
from PySide6.QtWidgets import (
    QWidget, QLabel, QSizePolicy, QLCDNumber, QPushButton, QGroupBox,
    QVBoxLayout, QGridLayout, QApplication, QFrame, QDial,
    QDoubleSpinBox, QToolBar, QDialog, QDialogButtonBox, QMessageBox,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QPlainTextEdit,
    QFormLayout, QHBoxLayout,
)
import PySide6QtAds as QtAds
from pypylon import pylon
from pyqtgraph import setConfigOptions, PlotWidget, mkPen, mkBrush

from dirs import BASE_DATA_PATH
from event_filter_cal import EventFilterCal
from image_processing import DetectedEllipse
from minimizer import PSCurrentsInfo, ObjectiveFunctionInfo
import resources  # noqa: F401

setConfigOptions(
    antialias=True,
    background='w', 
    foreground='k',
)

class FullScreenWindow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # self.parent = parent

        self.parentLayout = self.parentWidget().tab1.layout
        self.setLayout(self.parentLayout())
        # self.fullLayout = QHBoxLayout(self)
        # self.fullLayout.addWidget(self.parentWidget().video_label)
        # self.fullLayout.addChildWidget(self.parentWidget().toolbarVideoLabel.setalignment)
        self.setScreen(self.parentWidget().screen())
        self.setWindowFlags(Qt.WindowType.Window)
        self.showFullScreen()
        
        self.shortcutExitFullScreen = QShortcut(QKeySequence('Escape'), self)
        self.shortcutExitFullScreen.activated.connect(self.parentWidget().actionOpenInFullScreen.trigger)
    
    # def closeEvent(self, event):
    #     if self.parentWidget().actionOpenInWindow.isChecked():
    #         self.parentWidget().actionOpenInWindow.trigger()
    #     self.parentWidget().setLayout(self.parentLayout)

    #     return super().closeEvent(event)

class CameraCalibrationDialog(QDialog):
    calibrationFinished = Signal(list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent

        self.setWindowTitle("Camera Calibration")
        buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QDialogButtonBox(buttons)
        self.buttonBox.accepted.connect(self.accept)
        self.buttonBox.rejected.connect(self.reject)

        self.single_button = QPushButton("Single", self)
        self.single_button.setSizePolicy(
            QSizePolicy.Policy.Fixed,
            QSizePolicy.Policy.Fixed
        )
        # self.setWindowState(Qt.WindowState.WindowFullScreen)
        self.single_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.single_button.clicked.connect(self.get_single_image)

        self.label = LiveCameraFeedWidget(self)
        # Better to create a new event filter specifically for this purpose
        self.event_filter = EventFilterCal(self.label)
        # event_filter.positionChanged.connect(self.onPositionChanged)
        self.im = cv2.imread("100mesh_x16.tiff", cv2.IMREAD_GRAYSCALE)
        self.label.setImage(self.im)

        self.layout = QVBoxLayout()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.single_button, alignment=Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
    
    @Slot()
    def get_single_image(self):
        if self.parent.camera.IsGrabbing():
            self.parent.camera.StopGrabbing()

        temp_img = pylon.PylonImage()
        with self.parent.camera.GrabOne(1000) as grab:
            temp_img.AttachGrabResultBuffer(grab)
            # temp_img = pylon.PylonImage(grab)
            img = grab.GetArray()
            print("Got one image.")
            
            self.label.setImage(img)
            temp_img.Release()

    def drawPoint(self, point, pixmap):
        painter = QPainter(pixmap)
        pen = painter.pen()
        pen.setWidth(2)
        pen.setColor(QColor(0, 255, 0))
        painter.setPen(pen)
        brush = painter.brush()
        brush.setColor(QColor(0, 255, 0))
        brush.setStyle(Qt.BrushStyle.SolidPattern)
        painter.setBrush(brush)
        painter.drawEllipse(point, 4, 4)
        painter.end()
        self.label.setPixmap(pixmap)
    
    @Slot()
    def accept(self):
        calibrationParams = list(
            [
            self.event_filter.p1.toTuple(),
            self.event_filter.p2.toTuple(),
            self.event_filter.p3.toTuple(),
            self.event_filter.p4.toTuple(),
            self.event_filter.p5.toTuple()
            ]
        )
        if None not in calibrationParams:
            cal = self.calibrate(calibrationParams)
            self.calibrationFinished.emit(cal)

        return super().accept()

    @Slot()
    def reject(self):
        return super().reject()
    
    def calibrate(self, points:list) -> tuple:
        # Receive a list of tuples, representing the coordinates (x, y) chosen in the calibration dialog
        # Sort the points in the x direction. This will give us the left and right points
        x_sorted = sorted(points, key=lambda p: p[0])
        print('p3=', x_sorted[0])
        print('p4=', x_sorted[-1])

        # Sort in the y direction. This will give us the top and bottom points
        y_sorted = sorted(points, key=lambda p: p[1])
        print('p1=', y_sorted[0])
        print('p2=', y_sorted[-1])

        # Save them in a list
        sorted_points = [y_sorted[0], y_sorted[-1], x_sorted[0], x_sorted[-1]]

        # Find the remaining element. Below code is shorthand for this:
        # for p in points:
        #     if p not in sorted_points:
        #         center_point = p
        center_point, = (p for p in points if p not in sorted_points)
        print('p5=', center_point)

        # Calculate distances
        d = [dist(center_point, p) for p in sorted_points]
        print('distances from the central point: ', d)
        y_cal = (d[0] + d[1]) / 2
        x_cal = (d[2] + d[3]) / 2
        print(
            f'cal of x: {x_cal}\n'
            f'cal of y: {y_cal}'
        )
        return (x_cal, y_cal)

class NewWindow(QWidget):
    def __init__(self, title: str, widget: QWidget, parent=None):
        super().__init__(widget)
        self.title = title
        self.widget = widget

        # self.parentLayout = self.parentWidget().layout()
        self.parentLayout = self.widget.layout()
        self.setWindowTitle(title)
        self.setWindowFlags(Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setLayout(self.parentLayout)
        self.show()
    
    def closeEvent(self, event):
        if self.widget.actionOpenInWindow.isChecked():
            self.widget.actionOpenInWindow.trigger()
        self.widget.setLayout(self.parentLayout)
        
        return super().closeEvent(event)

class HistogramsWidget(QWidget):
    def __init__(self, parent=None):
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
            pen=mkPen({'color': "#1f77b4"}),  
            # fillBrush=pg.mkBrush("#1f77b4"), 
            name="y_profile"
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
            pen=mkPen({'color': "#1f77b4"}),  
            # fillBrush=pg.mkBrush("#1f77b4"), 
            name="x_profile"
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
            pen=mkPen({'color': "#1f77b4"}),  
            # fillBrush=pg.mkBrush("#1f77b4"), 
            name="hist"
        )

        self.dock_widget3 = QtAds.CDockWidget("ROI Histogram")
        self.dock_widget3.setContentsMargins(5, 5, 10, 5)
        self.dock_widget3.setWidget(self.pw3)
        manager.addDockWidget(QtAds.BottomDockWidgetArea, self.dock_widget3)

        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(16, 16))
        self.actionOpenInWindow = QAction("Open in window", self)
        self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg")))
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
    def updateHistHor(self, h):
        self.hor_data = h
        self.item1.setData(range(len(self.hor_data) + 1), self.hor_data)
    
    @Slot(ndarray)
    def updateHistVert(self, v):
        self.vert_data = v
        self.item2.setData(range(len(self.vert_data) + 1), self.vert_data)

    @Slot(ndarray)
    def updateHist(self, v):
        self.hist_data = v
        self.item3.setData(range(len(self.hist_data) + 1), self.hist_data)
    
    @Slot()
    def onActionOpenWindowClicked(self, checked):
        if checked:
            self.histogramsWindow = NewWindow("Histograms", self)
            self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-to-bracket-solid.svg")))
            self.actionOpenInWindow.setText("Return to main window")
        else:
            self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg")))
            self.histogramsWindow.close()
            self.actionOpenInWindow.setText("Open in window")
            self.histogramsWindow = None
    
    @Slot()
    def onActionClearData(self):
        self.hor_data = []
        self.vert_data = []
        self.hist_data = []

        self.item1.setData(self.hor_data)
        self.item2.setData(self.vert_data)
        self.item3.setData(self.hist_data)


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
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.data = RunData()

        QtAds.CDockManager.setConfigFlags(QtAds.CDockManager.DefaultNonOpaqueConfig)
        QtAds.CDockManager.setConfigFlag(QtAds.CDockManager.RetainTabSizeWhenCloseButtonHidden, True)
        QtAds.CDockManager.setAutoHideConfigFlags(QtAds.CDockManager.DefaultAutoHideConfig)
        # QtAds.CDockManager.setAutoHideConfigFlag(QtAds.CDockManager.AutoHideShowOnMouseOver, True)
        manager = QtAds.CDockManager()

        self.pw1 = PlotWidget()
        self.graph1 = self.pw1.getPlotItem()
        self.graph1.showAxes(True)
        self.graph1.setTitle("Ellipse Axes")
        self.graph1.setLabels(left="Length [px]", bottom="Count")
        self.graph1.addLegend(pen='k', brush='w', labelTextSize='8pt', colCount=2)
        self.item1 = self.graph1.plot(
            self.data.major,
            pen=mkPen({'color': "#1f77b4", 'width': 2}), 
            symbol='o', 
            symbolPen=mkPen({'color': "#1f77b4", 'width': 1}), 
            symbolBrush=mkBrush("#1f77b4"),
            symbolSize=5,
            name="Major"
        )
        self.item2 = self.graph1.plot(
            self.data.minor,
            pen=mkPen({'color': "#ff7f0e", 'width': 2}),
            symbol='o', 
            symbolPen=mkPen({'color': "#ff7f0e", 'width': 1}),
            symbolBrush=mkBrush("#ff7f0e"),
            symbolSize=5,
            name="Minor"
        )
        # self.grid = pg.GridItem(pen='k', textPen=None)
        # self.grid.setTickSpacing(x=[1.0, None], y=[1.0, None])
        # self.graph.addItem(self.grid)
        # self.graph.showGrid(x=True, y=True)

        self.dock_widget1 = QtAds.CDockWidget("Ellipse Axes")
        self.dock_widget1.setContentsMargins(5, 5, 10, 5)
        self.dock_widget1.setWidget(self.pw1)
        i = manager.addDockWidget(QtAds.LeftDockWidgetArea, self.dock_widget1)

        self.pw2 = PlotWidget()
        self.graph2 = self.pw2.getPlotItem()
        self.graph2.showAxes(True)
        self.graph2.setTitle("Quadrupole Currents")
        self.graph2.setLabels(left="Current [A]", bottom="Count")
        self.graph2.addLegend(pen='k', brush='w', labelTextSize='8pt', colCount=2)
        self.item3 = self.graph2.plot(
            self.data.current1, 
            pen=mkPen({'color': "#1f77b4", 'width': 2}), 
            symbol='o', 
            symbolPen=mkPen({'color': "#1f77b4", 'width': 1}), 
            symbolBrush=mkBrush("#1f77b4"), 
            symbolSize=5,
            name="PS1"
        )
        self.item4 = self.graph2.plot(
            self.data.current2,
            pen=mkPen({'color': "#ff7f0e", 'width': 2}),
            symbol='o', 
            symbolPen=mkPen({'color': "#ff7f0e", 'width': 1}),
            symbolBrush=mkBrush("#ff7f0e"),
            symbolSize=5,
            name="PS2"
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
        h = manager.addDockWidget(QtAds.RightDockWidgetArea, self.dock_widget2)

        self.pw3 = PlotWidget()
        self.graph3 = self.pw3.getPlotItem()
        self.graph3.showAxes(True)
        self.graph3.setTitle("Minimization Function")
        self.graph3.setLabels(left="Value [px⁴]", bottom="Count")
        self.graph3.getAxis('left').enableAutoSIPrefix(False)
        self.graph3.setLogMode(x=False, y=True)
        # self.graph3.addLegend(pen='k', labelTextSize='10pt')
        self.item5 = self.graph3.plot(
            self.data.cost_func, 
            pen=mkPen({'color': "#1f77b4", 'width': 2}), 
            symbol='o', 
            symbolPen=mkPen({'color': "#1f77b4", 'width': 1}), 
            symbolBrush=mkBrush("#1f77b4"), 
            symbolSize=5,
            name="MinFunc"
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
        self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg")))
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
    def updatePlotCurrents(self, x):
        self.data.current1.append(x[0])
        self.data.current2.append(x[1])

        self.item3.setData(self.data.current1)
        self.item4.setData(self.data.current2)
    
    @Slot(float)
    def updatePlotFunction(self, v):
        self.data.cost_func.append(v)
        self.item5.setData(self.data.cost_func)
    
    @Slot()
    def onActionOpenWindowClicked(self, checked):
        if checked:
            self.plottingWindow = NewWindow("Plotting", self)
            self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-to-bracket-solid.svg")))
            self.actionOpenInWindow.setText("Return to main window")
        else:
            self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg")))
            self.plottingWindow.close()
            self.actionOpenInWindow.setText("Open in window")
            self.plottingWindow = None
    
    @Slot()
    def onActionSaveData(self, path=None):
        if not path or not path.exists():
            path = BASE_DATA_PATH / date.today().isoformat()
            path.mkdir(parents=True, exist_ok=True)
        filename = path / f'data_{date.today()}_{time.time_ns()}.csv'
        with filename.open(mode='w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Count", "xc", "yc", "minor", "major", "angle", "Q1", "Q2", "Function"])
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
                    fillvalue=nan
                    )
                ):
                writer.writerow([row, *line])
        
        QMessageBox.information(
            self,
            "Data saved",
            f'Data were successfully saved to {filename}.',
            QMessageBox.StandardButton.Ok
        )

    @Slot()
    def onActionClearData(self):
        self.data.clear_data()

        self.item1.setData(self.data.major)
        self.item2.setData(self.data.minor)
        self.item3.setData(self.data.current1)
        self.item4.setData(self.data.current2)
        self.item5.setData(self.data.cost_func)


class PowerSupplyWidget(QWidget):
    def __init__(self, title=None, parent=None):
        super().__init__(parent)
        self.parent = parent
        
        self.voltageLCD = QLCDNumber(7)
        self.voltageLCD.display("  OFF  ")
        self.voltageLCD.setSegmentStyle(QLCDNumber.Flat)
        # self.voltageLCD.setMinimumHeight(70)
        self.voltageLCD.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )
        # self.voltageLCD.setFrameStyle(QFrame.NoFrame)
        self.voltageLCD.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Plain)
        
        self.currentLCD = QLCDNumber(7)
        self.currentLCD.display("  OFF  ")
        self.currentLCD.setSegmentStyle(QLCDNumber.Flat)
        # self.currentLCD.setMinimumHeight(70)
        self.currentLCD.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
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
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )
        # self.voltageDial.setValue(40)
        # self.voltageDial.valueChanged.connect(self.sliderVoltageMoved)

        self.spinboxVoltage = QDoubleSpinBox()
        self.spinboxVoltage.setRange(0.0, 6.0)
        self.spinboxVoltage.setDecimals(4)
        self.spinboxVoltage.clear()

        self.buttonVoltage = QPushButton('Set')
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
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
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

        self.buttonCurrent = QPushButton('Set')
        self.buttonCurrent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.buttonCurrent.clicked.connect(self.currentSetManually)

        displayLayout = QGridLayout()
        displayLayout.addWidget(QLabel("Voltage"), 0, 0, 1, 2, Qt.AlignmentFlag.AlignHCenter)
        displayLayout.addWidget(self.voltageLCD, 1, 0, 1, 2)
        displayLayout.addWidget(self.voltageDial, 2, 0, 1, 2)
        displayLayout.addWidget(self.buttonVoltage, 3, 0, 1, 1)
        displayLayout.addWidget(self.spinboxVoltage, 3, 1, 1, 1)

        displayLayout.addWidget(QLabel("Current"), 0, 2, 1, 2, Qt.AlignmentFlag.AlignHCenter)
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
        self.currentLCD.display(f'{self.currentDial.value() / 100:4.2f}')

    @Slot()
    def currentSetManually(self):
        v = self.spinboxCurrent.value()
        # print(v)
        v_int = int(v * 100)
        # print(v_int)
        self.currentDial.setValue(v_int)
    
    @Slot()
    def sliderVoltageMoved(self):
        self.voltageLCD.display(f'{self.voltageDial.value() / 10_000:.4f}')

    @Slot()
    def voltageSetManually(self):
        v = self.spinboxVoltage.value()
        # print(v)
        v_int = int(v * 10000)
        # print(v_int)
        self.voltageDial.setValue(v_int)
    
    def eventFilter(self, source, event):
        if (isinstance(source, QDial) and isinstance(event, QMouseEvent)):
            # event.ignore()
            return True

        return super().eventFilter(source, event)


class LiveCameraFeedWidget(QGraphicsView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.pxmap = None
        self.scale_factor = 1.25
        self.p_i = None
        self.p_f = None
        self.drawing = False
        self.roi = False
        self.roi_draw = True
        self.p_cross_x40 = None
        self.p_cross_x16 = None
        self.draw_crosshair_x40 = False
        self.draw_crosshair_x16 = False
        self.pts_scan_x40 = []
        self.pts_scan_x16 = []
        self.draw_scan_x40 = False
        self.draw_scan_x16 = False
        self.pen_width = None
        self.font_width = None
        
        self.setMinimumSize(642, 482)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.viewport().setCursor(Qt.CursorShape.CrossCursor)
        self.graphics_scene = QGraphicsScene(self)
        self.graphics_scene.setSceneRect(QRectF(0, 0, 640, 480))
        self.setScene(self.graphics_scene)

        self.pixmap = QGraphicsPixmapItem()
        self.pixmap.setShapeMode(QGraphicsPixmapItem.ShapeMode.BoundingRectShape)
        self.graphics_scene.addItem(self.pixmap)

    @Slot(QImage)
    def setImage(self, image: QImage) -> None:
        self.pixmap.setPixmap(self.drawRegions(QPixmap.fromImage(image)).scaled(self.viewport().size(), Qt.AspectRatioMode.KeepAspectRatio))
        self.pixmap.setPos(self.scene().sceneRect().center() - self.pixmap.boundingRect().center())

    def drawRegions(self, pixmap: QPixmap) -> QPixmap:
        if self.roi_draw or self.draw_crosshair_x40 or self.draw_crosshair_x16 or self.draw_scan_x40 or self.draw_scan_x16:
            with QPainter(pixmap) as painter:
                if self.pen_width is None or self.font_width is None:
                    self.pen_width = round(self.parent.camera.width * 0.004)
                    self.font_width = round(self.parent.camera.width * 0.015)
                painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.TextAntialiasing)
                pen = painter.pen()
                pen.setWidth(self.pen_width)
                font = painter.font()
                font.setPointSize(self.font_width)
                painter.setFont(font)

                if self.p_i and self.p_f and self.roi_draw:
                    self.drawROI(painter, pen)
                if self.p_cross_x40 is not None and self.draw_crosshair_x40:
                    self.drawCrosshairX40(painter, pen)
                if self.p_cross_x16 is not None and self.draw_crosshair_x16:
                    self.drawCrosshairX16(painter, pen)
                if self.pts_scan_x40 and self.draw_scan_x40:
                    self.drawScanRegionX40(painter, pen)
                if self.pts_scan_x16 and self.draw_scan_x16:
                    self.drawScanRegionX16(painter, pen)
        return pixmap

    def drawROI(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor(0, 255, 0))
        painter.setPen(pen)
        painter.drawRect(self.p_i.x(), self.p_i.y(), self.p_f.x() - self.p_i.x(), self.p_f.y() - self.p_i.y())
        painter.drawText(self.p_i.x() + 1.5 * self.pen_width, self.p_i.y() - self.font_width, "ROI")

    def drawCrosshairX40(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor(255, 0, 255))
        painter.setPen(pen)
        painter.drawLine(0, self.p_cross_x40.y(), self.parent.camera.width, self.p_cross_x40.y())
        painter.drawLine(self.p_cross_x40.x(), 0, self.p_cross_x40.x(), self.parent.camera.height)
        painter.drawText(self.p_cross_x40.x() + 1.5 * self.pen_width, self.font_width + 5, "x40")

    def drawCrosshairX16(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor(255, 0, 0))
        painter.setPen(pen)
        painter.drawLine(0, self.p_cross_x16.y(), self.parent.camera.width, self.p_cross_x16.y())
        painter.drawLine(self.p_cross_x16.x(), 0, self.p_cross_x16.x(), self.parent.camera.height)
        painter.drawText(self.p_cross_x16.x() + 1.5 * self.pen_width, self.font_width + 5, "x16")

    def drawScanRegionX40(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor(255, 255, 0))
        painter.setPen(pen)
        if len(self.pts_scan_x40) < 4:
            painter.drawPoints(self.pts_scan_x40)
        else:
            polygon = QPolygon(self.pts_scan_x40)
            painter.drawPolygon(polygon)
            painter.drawText(polygon.boundingRect().topLeft() + QPoint(2 * self.pen_width, -self.font_width), "Scan x40")

    def drawScanRegionX16(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor("orange"))
        painter.setPen(pen)
        if len(self.pts_scan_x16) < 4:
            painter.drawPoints(self.pts_scan_x16)
        else:
            polygon = QPolygon(self.pts_scan_x16)
            painter.drawPolygon(self.pts_scan_x16)
            painter.drawText(polygon.boundingRect().topLeft() + QPoint(2 * self.pen_width, -self.font_width), "Scan x16")

    def resizeEvent(self, event):
        self.scene().setSceneRect(self.scene().itemsBoundingRect())
        super().resizeEvent(event)

    def sizeHint(self):
        return QSize(642, 482)


class ImageProcessingQLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    @Slot(ndarray)
    def setImage(self, image: ndarray) -> None:
        if image.ndim == 2:
            h, w = image.shape
            image = QImage(image.data, w, h, w, QImage.Format.Format_Grayscale8)
        elif image.ndim == 3:
            h, w, ch = image.shape
            image = QImage(image.data, w, h, ch * w, QImage.Format.Format_RGB888)

        self.setPixmap(QPixmap.fromImage(image).scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio))

    def sizeHint(self):
        return QSize(640, 480)

class ImageProcessingWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.imageProcessingWindow = None
        self.video_label = ImageProcessingQLabel(self)

        self.actionOpenInWindow = QAction("Open in window", self)
        self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg")))
        self.actionOpenInWindow.setCheckable(True)
        self.actionOpenInWindow.triggered.connect(self.onActionOpenWindowClicked)

        self.toolbar = QToolBar(self)
        self.toolbar.setIconSize(QSize(16, 16))
        self.toolbar.addAction(self.actionOpenInWindow)

        self.ps1_previous_label = QLabel("nan")
        self.ps2_previous_label = QLabel("nan")
        self.ps1_min_label = QLabel("nan")
        self.ps2_min_label = QLabel("nan")

        formPSCurrentsStats = QFormLayout()
        formPSCurrentsStats.addRow("Last PS1:", self.ps1_previous_label)
        formPSCurrentsStats.addRow("Last PS2:", self.ps2_previous_label)
        formPSCurrentsStats.addRow("Min. PS1:", self.ps1_min_label)
        formPSCurrentsStats.addRow("Min. PS2:", self.ps2_min_label)
        
        self.obj_func_previous_label = QLabel("nan")
        self.obj_func_delta_label = QLabel("nan")
        self.obj_func_min_label = QLabel("nan")
        self.obj_func_min_delta_label = QLabel("nan")

        formObjFuncStats = QFormLayout()
        formObjFuncStats.addRow("{:<16}".format("Last obj. func.:"), self.obj_func_previous_label)
        formObjFuncStats.addRow("{:<16}".format("Min. obj. func.:"), self.obj_func_min_label)
        formObjFuncStats.addRow("{:<16}".format("Last delta:"), self.obj_func_delta_label)
        formObjFuncStats.addRow("{:<16}".format("Min. delta:"), self.obj_func_min_delta_label)

        minimizerStats = QHBoxLayout()
        minimizerStats.addLayout(formPSCurrentsStats)
        minimizerStats.addLayout(formObjFuncStats)
        
        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.video_label)
        layout.addLayout(minimizerStats)
        self.setLayout(layout)
    
    @Slot()
    def onActionOpenWindowClicked(self, checked):
        if checked:
            self.imageProcessingWindow = NewWindow("Processed Feed", self)
            self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-to-bracket-solid.svg")))
            self.actionOpenInWindow.setText("Return to main window")
        else:
            self.actionOpenInWindow.setIcon(QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg")))
            self.imageProcessingWindow.close()
            self.actionOpenInWindow.setText("Open in window")
            self.imageProcessingWindow = None
    
    @Slot(PSCurrentsInfo, ObjectiveFunctionInfo)
    def onMinimizerFuncEvalUpdate(self, ps_currents: PSCurrentsInfo, obj_func: ObjectiveFunctionInfo) -> None:
        self.ps1_previous_label.setText(f"{ps_currents.ps1_previous:.4f}")
        self.ps2_previous_label.setText(f"{ps_currents.ps2_previous:.4f}")
        self.ps1_min_label.setText(f"{ps_currents.ps1_min:.4f}")
        self.ps2_min_label.setText(f"{ps_currents.ps2_min:.4f}")
        self.obj_func_previous_label.setText(f"{obj_func.previous:.4f}")
        self.obj_func_min_label.setText(f"{obj_func.min_val:.4f}")
        self.obj_func_delta_label.setText(f"{obj_func.delta:.4f}")
        self.obj_func_min_delta_label.setText(f"{obj_func.min_delta:.4f}")


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
        self.log_output.setMaximumBlockCount(1500)

        font = QFont('nosuchfont')
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


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    
    window = PowerSupplyWidget()
    window.show()    
    
    sys.exit(app.exec())
    # app.exec()
    # app.shutdown()