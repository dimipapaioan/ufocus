# -*- coding: utf-8 -*-

from numpy import ndarray
from PySide6.QtCore import Slot, QSize
from PySide6.QtGui import QPixmap, QAction, QIcon
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QToolBar,
)
import PySide6QtAds as QtAds
from pyqtgraph import setConfigOptions, PlotWidget, mkPen

from .floating_widget import FloatingWidget
import resources  # noqa: F401

setConfigOptions(
    antialias=True,
    background='w', 
    foreground='k',
)


# class CameraCalibrationDialog(QDialog):
#     calibrationFinished = Signal(list)

#     def __init__(self, parent=None):
#         super().__init__(parent)
#         self.parent = parent

#         self.setWindowTitle("Camera Calibration")
#         buttons = QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel

#         self.buttonBox = QDialogButtonBox(buttons)
#         self.buttonBox.accepted.connect(self.accept)
#         self.buttonBox.rejected.connect(self.reject)

#         self.single_button = QPushButton("Single", self)
#         self.single_button.setSizePolicy(
#             QSizePolicy.Policy.Fixed,
#             QSizePolicy.Policy.Fixed
#         )
#         # self.setWindowState(Qt.WindowState.WindowFullScreen)
#         self.single_button.setCursor(Qt.CursorShape.PointingHandCursor)
#         self.single_button.clicked.connect(self.get_single_image)

#         self.label = LiveCameraFeedWidget(self)
#         # Better to create a new event filter specifically for this purpose
#         self.event_filter = EventFilterCal(self.label)
#         # event_filter.positionChanged.connect(self.onPositionChanged)
#         self.im = cv2.imread("100mesh_x16.tiff", cv2.IMREAD_GRAYSCALE)
#         self.label.setImage(self.im)

#         self.layout = QVBoxLayout()
#         self.layout.addWidget(self.label)
#         self.layout.addWidget(self.single_button, alignment=Qt.AlignmentFlag.AlignCenter)
#         self.layout.addWidget(self.buttonBox)
#         self.setLayout(self.layout)
    
#     @Slot()
#     def get_single_image(self):
#         if self.parent.camera.IsGrabbing():
#             self.parent.camera.StopGrabbing()

#         temp_img = pylon.PylonImage()
#         with self.parent.camera.GrabOne(1000) as grab:
#             temp_img.AttachGrabResultBuffer(grab)
#             # temp_img = pylon.PylonImage(grab)
#             img = grab.GetArray()
#             print("Got one image.")
            
#             self.label.setImage(img)
#             temp_img.Release()

#     def drawPoint(self, point, pixmap):
#         painter = QPainter(pixmap)
#         pen = painter.pen()
#         pen.setWidth(2)
#         pen.setColor(QColor(0, 255, 0))
#         painter.setPen(pen)
#         brush = painter.brush()
#         brush.setColor(QColor(0, 255, 0))
#         brush.setStyle(Qt.BrushStyle.SolidPattern)
#         painter.setBrush(brush)
#         painter.drawEllipse(point, 4, 4)
#         painter.end()
#         self.label.setPixmap(pixmap)
    
#     @Slot()
#     def accept(self):
#         calibrationParams = list(
#             [
#             self.event_filter.p1.toTuple(),
#             self.event_filter.p2.toTuple(),
#             self.event_filter.p3.toTuple(),
#             self.event_filter.p4.toTuple(),
#             self.event_filter.p5.toTuple()
#             ]
#         )
#         if None not in calibrationParams:
#             cal = self.calibrate(calibrationParams)
#             self.calibrationFinished.emit(cal)

#         return super().accept()

#     @Slot()
#     def reject(self):
#         return super().reject()
    
#     def calibrate(self, points:list) -> tuple:
#         # Receive a list of tuples, representing the coordinates (x, y) chosen in the calibration dialog
#         # Sort the points in the x direction. This will give us the left and right points
#         x_sorted = sorted(points, key=lambda p: p[0])
#         print('p3=', x_sorted[0])
#         print('p4=', x_sorted[-1])

#         # Sort in the y direction. This will give us the top and bottom points
#         y_sorted = sorted(points, key=lambda p: p[1])
#         print('p1=', y_sorted[0])
#         print('p2=', y_sorted[-1])

#         # Save them in a list
#         sorted_points = [y_sorted[0], y_sorted[-1], x_sorted[0], x_sorted[-1]]

#         # Find the remaining element. Below code is shorthand for this:
#         # for p in points:
#         #     if p not in sorted_points:
#         #         center_point = p
#         center_point, = (p for p in points if p not in sorted_points)
#         print('p5=', center_point)

#         # Calculate distances
#         d = [dist(center_point, p) for p in sorted_points]
#         print('distances from the central point: ', d)
#         y_cal = (d[0] + d[1]) / 2
#         x_cal = (d[2] + d[3]) / 2
#         print(
#             f'cal of x: {x_cal}\n'
#             f'cal of y: {y_cal}'
#         )
#         return (x_cal, y_cal)


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
            self.histogramsWindow = FloatingWidget("Histograms", self)
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
