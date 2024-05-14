# -*- coding: utf-8 -*-

import logging

from pypylon import pylon
from PySide6.QtCore import (
    Qt, Slot, QPoint, QSize,
    QThreadPool, QMutex, QWaitCondition,
)
from PySide6.QtGui import (
    QAction, QIcon, QPixmap, QColor, QPainter, QTransform, QImage,
)
from PySide6.QtWidgets import (
    QApplication, QLabel, QMainWindow, QPushButton, QScrollArea,
    QVBoxLayout, QHBoxLayout, QWidget, QCheckBox, QStatusBar,
    QMessageBox, QTabWidget, QGridLayout, QGroupBox, QSpinBox,
    QDoubleSpinBox, QComboBox, QSlider, QToolBar, QFormLayout,
    QFileDialog,
)
import serial
from serial.tools.list_ports import comports

from camera_worker import CameraWorkerR
from dirs import BASE_PATH
from event_filter import EventFilter
from image_processing import ImageProcessing
from minimizer import Minimizer
from ps_controller import PSController
import resources
from settings_manager import SettingsManager
from widgets import (
    LiveCameraFeedWidget, ImageProcessingWidget, PowerSupplyWidget, 
    PlottingWidget, HistogramsWidget, CameraCalibrationDialog,
    FullScreenWindow,
)

CUSTOM_STYLESHEET = """
    QLCDNumber {
        border: 1px solid lightgray;
        border-radius: 10px;
        padding: 10px;
        background-color: lightgray;
    }

    QLCDNumber:enabled {
        color: black;
    }

    QLCDNumber:disabled {
        color: gray;
    }

    QToolTip {
        border: 1px solid black;
        padding: 2%;
        background-color: lightgrey;
        color: black;
    }
    FullScreenWindow {
        background-color: black;
        padding: 2%;
        color: lightgrey;
    }

    FullScreenWindow QWidget {
        background-color: black;
        padding: 2%;
        color: lightgrey;
    }

    FullScreenWindow QToolButton {
        border-radius: 4px;
        padding: 4%;
    }

    FullScreenWindow QToolButton:hover {
        border: 1px solid #808080;
    }

    FullScreenWindow QToolButton:hover:pressed {
        border: 1px solid #404040;
    }

    FullScreenWindow QToolTip {
        border: 1px solid lightgrey;
        padding: 2%;
        background-color: black;
        color: lightgrey;
    }

    QWidget {
        font: "Inter"
    }
"""

ABOUT = """
<p><b><font size='+1'>The μFocus Application</font></b></p>
<p>Version: 2.1.0</p>
<p>Author: Dimitrios Papaioannou
<a href = "mailto: dimipapaioan@outlook.com"> dimipapaioan@outlook.com </a> </p>
"""

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ports = self.list_ports()
        self.serial_port = None
        self.factory = pylon.TlFactory.GetInstance()
        self.devices = self.list_cameras()
        self.camera = None
        self.threadpool = QThreadPool(self)
        self.settings_manager = SettingsManager(self)
        self.initUI()
        self.settings_manager.setUserValues()

        logger.info("Application started successfully")

    def list_ports(self):
        ports = comports()
        if ports:
            logger.info("Serial ports found")
            return ports
        else:
            logger.warning("No serial ports in the system")
            return []

    def connect_port(self, port):
        try:
            serial_port = serial.Serial(
                port=port,
                baudrate=9600,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.5,
                write_timeout=0.5
            )

            if serial_port.is_open:
                logger.info("Port opened successfully")

        except serial.SerialException:
            logger.error("Could not open port")

        except IOError:  # if port is already opened, close it and open it again
            serial_port.close()
            serial_port.open()
            if serial_port.is_open:
                logger.error("Port was open, closed and opened it again.")

        else:
            return serial_port

    def disconnect_port(self, serial_port: serial.Serial):
        serial_port.close()
        if serial_port.is_open:
            logger.warning("Port is still open")
        else:
            logger.info("Port closed")

        # self.serial_port = None

    def list_cameras(self):
        devices = self.factory.EnumerateDevices()
        if devices:
            logger.info("Camera devices found")
            return devices
        else:
            logger.warning("No camera devices found")
            return []

    def connect_camera(self, camera_idx):
        camera = pylon.InstantCamera(self.factory.CreateDevice(self.devices[camera_idx]))
        return camera

    def disconnect_camera(self, camera):
        if camera.IsGrabbing():
            camera.StopGrabbing()

        camera.Close()
        camera.DestroyDevice()

    def initUI(self):
        self.setWindowTitle("μFocus")
        self.setWindowIcon(QIcon(":icons/icon3_256.svg"))
        self.setStyleSheet(CUSTOM_STYLESHEET)

        # Initialize tab screen
        self.tabs = QTabWidget()
        self.tabs.setMovable(True)
        self.tab1 = QWidget()
        self.imageProcessingFeed = ImageProcessingWidget(self)
        self.plotting = PlottingWidget(self)
        self.histograms = HistogramsWidget(self)

        # Add tabs
        self.tabs.addTab(self.tab1, "Live Feed")
        self.tabs.addTab(self.imageProcessingFeed, "Processed Feed")
        self.tabs.addTab(self.plotting, "Plotting")
        self.tabs.addTab(self.histograms, "Histograms")

        # Create and connect widgets
        self.video_label = LiveCameraFeedWidget(self)
        # self.video_label.setText("Camera is closed.")
        self.event_filter = EventFilter(self.video_label)
        self.event_filter.positionChanged.connect(self.onPositionChanged)

        self.toolbarVideoLabel = QToolBar(self)
        self.toolbarVideoLabel.setIconSize(QSize(16, 16))

        self.actionOpenInFullScreen = QAction("Fullscreen", self)
        self.actionOpenInFullScreen.setIcon(QIcon(QPixmap(":/icons/expand-solid.svg")))
        self.actionOpenInFullScreen.setCheckable(True)
        self.actionOpenInFullScreen.triggered.connect(self.setFullScreen)
        self.toolbarVideoLabel.addAction(self.actionOpenInFullScreen)

        self.actionZoomIn = QAction("Zoom In", self)
        self.actionZoomIn.setIcon(QIcon(QPixmap(":/icons/magnifying-glass-plus-solid.svg")))
        self.actionZoomIn.setShortcut("Ctrl++")
        self.actionZoomIn.triggered.connect(self.zoom_in)
        self.toolbarVideoLabel.addAction(self.actionZoomIn)

        self.actionZoomOut = QAction("Zoom Out", self)
        self.actionZoomOut.setIcon(QIcon(QPixmap(":/icons/magnifying-glass-minus-solid.svg")))
        self.actionZoomOut.setShortcut("Ctrl+-")
        self.actionZoomOut.triggered.connect(self.zoom_out)
        self.actionZoomOut.setEnabled(False)
        self.toolbarVideoLabel.addAction(self.actionZoomOut)

        self.actionZoomRestore = QAction("Restore Zoom", self)
        self.actionZoomRestore.setIcon(QIcon(QPixmap(":/icons/magnifying-glass-solid.svg")))
        self.actionZoomRestore.setShortcut("Ctrl+0")
        self.actionZoomRestore.triggered.connect(self.zoom_restore)
        self.actionZoomRestore.setEnabled(False)
        self.toolbarVideoLabel.addAction(self.actionZoomRestore)

        self.actionSaveImageAs = QAction("Save Image As...", self)
        self.actionSaveImageAs.setIcon(QIcon(QPixmap(":/icons/floppy-disk-solid.svg")))
        self.actionSaveImageAs.setShortcut("Ctrl+Shift+S")
        self.actionSaveImageAs.triggered.connect(self.saveImage)
        self.actionSaveImageAs.setEnabled(False)
        self.toolbarVideoLabel.addAction(self.actionSaveImageAs)

        self.status_bar = QStatusBar(self)
        self.status_bar.setSizeGripEnabled(False)
        self.statusLabelFPS = QLabel("")
        self.statusLabelPosition = QLabel("")
        self.status_bar.addWidget(self.statusLabelFPS)
        self.status_bar.addWidget(self.statusLabelPosition)

        self.start_button = QPushButton("Start", self)
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.clicked.connect(self.continuous_capture)
        self.start_button.setEnabled(True)

        self.close_button = QPushButton("Stop", self)
        self.close_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_button.clicked.connect(self.stop_capture)
        self.close_button.setEnabled(False)

        self.single_button = QPushButton("Single", self)
        self.single_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.single_button.clicked.connect(self.get_single_image)
        self.single_button.setEnabled(True)

        self.roi_checkbox = QCheckBox("Show ROI", self)
        self.roi_checkbox.setChecked(self.settings_manager.user_settings['roi_draw'])
        self.roi_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.roi_checkbox.setToolTip(
            f"<p>Hold Left Click and drag the mouse on the Live Feed image to set a ROI.</p>"
            f"<p>Press Middle Click anywhere on the Live Feed image to unset it.</p>"
        )
        self.roi_checkbox.stateChanged.connect(self.onROIStateChanged)

        self.crosshair_x40_checkbox = QCheckBox("Show Crosshair x40", self)
        self.crosshair_x40_checkbox.setChecked(self.settings_manager.user_settings['draw_crosshair_x40'])
        self.crosshair_x40_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.crosshair_x40_checkbox.setToolTip(
            f"<p>Press Ctrl + Left Click on the Live Feed image to set a crosshair point.</p>"
            f"<p>Press Ctrl + Middle Click anywhere on the Live Feed image to unset it.</p>"
        )
        self.crosshair_x40_checkbox.stateChanged.connect(self.onCrosshairX40StateChanged)

        self.scan_x40_checkbox = QCheckBox("Show Scan Region x40", self)
        self.scan_x40_checkbox.setChecked(self.settings_manager.user_settings['draw_scan_x40'])
        self.scan_x40_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_x40_checkbox.setToolTip(
            f"<p>Press Ctrl + Alt + Left Click on the Live Feed image to select the points of the region to be marked.</p>"
            f"<p>Press Ctrl + Alt + Middle Click anywhere on the Live Feed image to unset all of them.</p>"
        )
        self.scan_x40_checkbox.stateChanged.connect(self.onScanX40StateChanged)

        self.crosshair_x16_checkbox = QCheckBox("Show Crosshair x16", self)
        self.crosshair_x16_checkbox.setChecked(self.settings_manager.user_settings['draw_crosshair_x16'])
        self.crosshair_x16_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.crosshair_x16_checkbox.setToolTip(
            f"<p>Press Ctrl + Shift + Left Click on the Live Feed image to set a crosshair point.</p>"
            f"<p>Press Ctrl + Shift + Middle Click anywhere on the Live Feed image to unset it.</p>"
        )
        self.crosshair_x16_checkbox.stateChanged.connect(self.onCrosshairX16StateChanged)

        self.scan_x16_checkbox = QCheckBox("Show Scan Region x16", self)
        self.scan_x16_checkbox.setChecked(self.settings_manager.user_settings['draw_scan_x16'])
        self.scan_x16_checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.scan_x16_checkbox.setToolTip(
            f"<p>Press Ctrl + Alt + Shift + Left Click on the Live Feed image to select the points of the region to be marked.</p>"
            f"<p>Press Ctrl + Alt + Shift + Middle Click anywhere on the Live Feed image to unset all of them.</p>"
        )
        self.scan_x16_checkbox.stateChanged.connect(self.onScanX16StateChanged)

        self.improc_button = QPushButton("Image Processing", self)
        self.improc_button.setCheckable(True)
        self.improc_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.improc_button.toggled.connect(self.onImprocStateChanged)

        self.spinboxImagesToAccumulate = QSpinBox(self)
        self.spinboxImagesToAccumulate.setRange(1, 500)
        # self.spinboxImagesToAccumulate.setValue(20)
        self.spinboxImagesToAccumulate.setKeyboardTracking(False)
        self.spinboxImagesToAccumulate.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxImagesToAccumulate": v})
        )

        self.spinboxThreshold = QSpinBox(self)
        self.spinboxThreshold.setRange(-1, 255)
        # self.spinboxThreshold.setValue(-1)
        self.spinboxThreshold.setKeyboardTracking(False)
        self.spinboxThreshold.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxThreshold": v})
        )

        self.checkboxGaussianFiltering = QCheckBox("Gaussian Filtering", self)
        self.checkboxGaussianFiltering.setChecked(False)
        self.checkboxGaussianFiltering.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkboxGaussianFiltering.stateChanged.connect(self.onGaussianFilterStateChanged)

        self.spinboxGaussianKernel = QSpinBox(self)
        self.spinboxGaussianKernel.setRange(1, 201)
        self.spinboxGaussianKernel.setSingleStep(2)
        # self.spinboxGaussianKernel.setValue(5)
        self.spinboxGaussianKernel.setKeyboardTracking(False)
        self.spinboxGaussianKernel.setEnabled(False)
        self.spinboxGaussianKernel.valueChanged.connect(
            lambda v: self.spinboxGaussianKernel.setValue(v-1) if v % 2 == 0 else self.spinboxGaussianKernel.setValue(v)
        )
        self.spinboxGaussianKernel.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxGaussianKernel": v})
        )

        self.checkboxSaveImages = QCheckBox("Save Images", self)
        self.checkboxSaveImages.setChecked(False)
        self.checkboxSaveImages.setCursor(Qt.CursorShape.PointingHandCursor)

        self.setupConnections()

        self.setupCameraOptions()

        self.setupMinimization()

        self.setupMainStatusBar()

        # Set the layout
        self.tab1.layout = QVBoxLayout()
        self.tab1.layout.addWidget(self.toolbarVideoLabel)
        self.tab1.layout.addWidget(self.video_label, Qt.AlignmentFlag.AlignCenter)
        self.tab1.layout.addWidget(self.status_bar)
        self.tab1.setLayout(self.tab1.layout)

        buttonLayout = QHBoxLayout()
        buttonLayout.addWidget(self.start_button)
        buttonLayout.addWidget(self.close_button)
        buttonLayout.addWidget(self.single_button)

        groupDisplayOptions = QGroupBox("Display Options")
        displayOptionsLayout = QFormLayout()
        displayOptionsLayout.setWidget(0, QFormLayout.ItemRole.SpanningRole, self.roi_checkbox)
        displayOptionsLayout.setWidget(1, QFormLayout.ItemRole.SpanningRole, self.crosshair_x40_checkbox)
        displayOptionsLayout.setWidget(2, QFormLayout.ItemRole.SpanningRole, self.crosshair_x16_checkbox)
        displayOptionsLayout.setWidget(3, QFormLayout.ItemRole.SpanningRole, self.scan_x40_checkbox)
        displayOptionsLayout.setWidget(4, QFormLayout.ItemRole.SpanningRole, self.scan_x16_checkbox)
        groupDisplayOptions.setLayout(displayOptionsLayout)

        groupImageProcessingOptions = QGroupBox("Image Processing Options")
        imageProcessingOptionsLayout = QFormLayout()
        imageProcessingOptionsLayout.addRow("Images:", self.spinboxImagesToAccumulate)
        imageProcessingOptionsLayout.setWidget(1, QFormLayout.ItemRole.SpanningRole, self.checkboxGaussianFiltering)
        imageProcessingOptionsLayout.addRow("Kernel:", self.spinboxGaussianKernel)
        imageProcessingOptionsLayout.addRow("Threshold:", self.spinboxThreshold)
        imageProcessingOptionsLayout.setWidget(4, QFormLayout.ItemRole.SpanningRole, self.checkboxSaveImages)
        
        mainImageProcessingLayout = QVBoxLayout()
        mainImageProcessingLayout.addLayout(imageProcessingOptionsLayout)
        mainImageProcessingLayout.addSpacing(20)
        mainImageProcessingLayout.addWidget(self.improc_button)
        groupImageProcessingOptions.setLayout(mainImageProcessingLayout)

        self.psLCD1 = PowerSupplyWidget("Q1 Power Supply", self)
        self.psLCD1.setEnabled(False)
        self.psLCD1.spinboxCurrent.valueChanged.connect(self.spinboxInitialPS1.setValue)
        self.psLCD2 = PowerSupplyWidget("Q2/Q3 Power Supply", self)
        self.psLCD2.setEnabled(False)
        self.psLCD2.spinboxCurrent.valueChanged.connect(self.spinboxInitialPS2.setValue)

        centerLayout = QGridLayout()
        centerLayout.addWidget(self.tabs, 0, 0)
        centerLayout.addLayout(buttonLayout, 1, 0, Qt.AlignmentFlag.AlignCenter)
        centerLayout.addWidget(self.groupCameraOptions, 2, 0)

        rightLayout = QGridLayout()
        rightLayout.addWidget(groupDisplayOptions, 0, 0)
        rightLayout.addWidget(groupImageProcessingOptions, 1, 0)
        rightLayout.addWidget(self.groupMinimizerOptions, 2, 0)

        mainLayout = QGridLayout()
        mainLayout.addWidget(self.groupConnection, 0, 0, 1, 2)
        mainLayout.addWidget(self.psLCD1, 1, 0, 3, 2)
        mainLayout.addWidget(self.psLCD2, 4, 0, 3, 2)
        mainLayout.addLayout(centerLayout, 0, 2, 7, 5)
        mainLayout.addLayout(rightLayout, 0, 7, 7, 2)

        # self.centralWidget = QWidget()
        # self.setCentralWidget(self.centralWidget)
        # self.centralWidget.setLayout(mainLayout)

        # Make the cantral widget scrollable
        self.centralWidget = QWidget(self)
        self.centralWidget.setLayout(mainLayout)

        self.scrollArea = QScrollArea(self)
        self.scrollArea.setWidget(self.centralWidget)
        self.scrollArea.setWidgetResizable(True)
        self.scrollArea.setMinimumSize(1000, 600)
        self.setCentralWidget(self.scrollArea)
        
        # Menu Bar
        menu = self.menuBar()

        menuFile = menu.addMenu("File")
        menuFile.addAction(self.actionSaveImageAs)
        menuFile.addAction(self.actionResetCamera)
        menuFile.addSeparator()
        menuFile.addAction(self.plotting.actionSaveData)
        menuFile.addAction(self.plotting.actionClearData)
        menuFile.addSeparator()
        menuFile.addAction('Save current settings', self.settings_manager.saveUserSettings, 'Ctrl+Alt+S')
        menuFile.addAction('Restore default settings', self.settings_manager.setDefaultValues)
        menuFile.addSeparator()
        menuFile.addAction('Quit', self.close, 'Ctrl+Q')

        menuTools = menu.addMenu("Tools")
        self.actionStartCalibration = QAction("Camera Calibration", self)
        self.actionStartCalibration.setStatusTip("Start camera calibration")
        self.actionStartCalibration.triggered.connect(self.calibrationDialogAction)
        menuTools.addAction(self.actionStartCalibration)

        menuView = menu.addMenu("View")
        menuView.addAction(self.actionOpenInFullScreen)
        menuView.addAction(self.actionZoomIn)
        menuView.addAction(self.actionZoomOut)
        menuView.addAction(self.actionZoomRestore)
        menuView.addSeparator()
        submenuImageProcessingFeed = menuView.addMenu("Processed Feed")
        submenuImageProcessingFeed.addAction(self.imageProcessingFeed.actionOpenInWindow)
        submenuPlotting = menuView.addMenu("Plotting")
        submenuPlotting.addAction(self.plotting.actionOpenInWindow)
        submenuPlotting.addAction(self.plotting.dock_widget1.toggleViewAction())
        submenuPlotting.addAction(self.plotting.dock_widget2.toggleViewAction())
        submenuPlotting.addAction(self.plotting.dock_widget3.toggleViewAction())
        submenuHistograms = menuView.addMenu("Histograms")
        submenuHistograms.addAction(self.histograms.actionOpenInWindow)
        submenuHistograms.addAction(self.histograms.dock_widget1.toggleViewAction())
        submenuHistograms.addAction(self.histograms.dock_widget2.toggleViewAction())
        submenuHistograms.addAction(self.histograms.dock_widget3.toggleViewAction())

        menuAbout = menu.addMenu("About")
        menuAbout.addAction('About', self.about)
        menuAbout.addAction('About Qt', QApplication.aboutQt)

    @Slot()
    def about(self):
        QMessageBox.about(self, "About μFocus", ABOUT)
    
    @Slot()
    def zoom_in(self):
        self.video_label.scale(self.video_label.scale_factor, self.video_label.scale_factor)
        self.updateZoomActions()

    @Slot()
    def zoom_out(self):
        self.video_label.scale(1 / self.video_label.scale_factor, 1 / self.video_label.scale_factor)
        self.updateZoomActions()

    @Slot()
    def zoom_restore(self):
        self.video_label.setTransform(QTransform(1.0, 0, 0, 0, 1.0, 0, 0, 0, 1.0))
        self.updateZoomActions()

    def updateZoomActions(self):
        self.actionZoomIn.setEnabled(self.video_label.transform().m11() < 30)
        self.actionZoomOut.setEnabled(self.video_label.transform().m11() > 1.0)
        self.actionZoomRestore.setEnabled(self.video_label.transform().m11() != 1.0)
    
    def calibrationDialogAction(self, s):
        if self.cal is not None:
            self.windowCalibration.stackedWidget.setCurrentWidget(self.windowCalibration.calibrationInfo)
        else:
            print("Camera calibration started")
            self.windowCalibration = CameraCalibrationDialog()
            self.windowCalibration.calibrationFinished.connect(
                lambda cal: print(cal)
            )
            self.windowCalibration.calibrationFinished.connect(self.calib)
        self.windowCalibration.show()
    
    @Slot(list)
    def calib(self, c):
        self.cal = c

    @Slot()
    def setFullScreen(self, pressed):
        if pressed:
            self.win = FullScreenWindow(self)
            pixmaps = (
                QPixmap(":/icons/compress-solid.svg"), 
                QPixmap(":/icons/magnifying-glass-plus-solid.svg"), 
                QPixmap(":/icons/magnifying-glass-minus-solid.svg"),
                QPixmap(":/icons/magnifying-glass-solid.svg"),
                QPixmap(":/icons/floppy-disk-solid.svg"),
            )
            painter = QPainter()
            for pixmap in pixmaps:
                painter.begin(pixmap)
                painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceIn)
                painter.fillRect(pixmap.rect(), QColor('lightgrey'))
                painter.end()
            self.actionOpenInFullScreen.setIcon(QIcon(pixmaps[0]))
            self.actionOpenInFullScreen.setToolTip("Exit FullScreen")
            self.actionZoomIn.setIcon(QIcon(pixmaps[1]))
            self.actionZoomOut.setIcon(QIcon(pixmaps[2]))
            self.actionZoomRestore.setIcon(QIcon(pixmaps[3]))
            self.actionSaveImageAs.setIcon(QIcon(pixmaps[4]))
        else:
            self.tab1.setLayout(self.tab1.layout)
            self.actionOpenInFullScreen.setIcon(QIcon(QPixmap(":/icons/expand-solid.svg")))
            self.actionOpenInFullScreen.setToolTip("FullScreen")
            self.actionZoomIn.setIcon(QIcon(QPixmap(":/icons/magnifying-glass-plus-solid.svg")))
            self.actionZoomOut.setIcon(QIcon(QPixmap(":/icons/magnifying-glass-minus-solid.svg")))
            self.actionZoomRestore.setIcon(QIcon(QPixmap(":/icons/magnifying-glass-solid.svg")))
            self.actionSaveImageAs.setIcon(QIcon(QPixmap(":/icons/floppy-disk-solid.svg")))
            self.win.close()

    def setupConnections(self):
        # Setup the serial port widgets
        self.comboboxSerial = QComboBox()
        # self.comboboxSerial.setMaximumWidth(200)

        self.connectionButtonSerial = QPushButton("Connect", self)
        self.connectionButtonSerial.setCheckable(True)
        self.connectionButtonSerial.setCursor(Qt.CursorShape.PointingHandCursor)
        # self.connectionButtonSerial.setMaximumWidth(100)

        if self.ports:
            for port in self.ports:
                self.comboboxSerial.addItem(port.description)
            self.comboboxSerial.setCurrentIndex(0)
        else:
            self.comboboxSerial.setPlaceholderText("No serial ports found...")
            self.connectionButtonSerial.setEnabled(False)
            self.comboboxSerial.setEnabled(False)

        # Setup the camera widgets
        self.comboboxCamera = QComboBox()
        # self.comboboxCamera.setMaximumWidth(200)

        self.connectionButtonCamera = QPushButton("Connect", self)
        self.connectionButtonCamera.setCheckable(True)
        self.connectionButtonCamera.setCursor(Qt.CursorShape.PointingHandCursor)
        # self.connectionButtonCamera.setMaximumWidth(100)

        if self.devices:
            for device in self.devices:
                self.comboboxCamera.addItem(device.GetFriendlyName())
            self.comboboxSerial.setCurrentIndex(1)
        else:
            self.comboboxCamera.setPlaceholderText("No camera found...")
            self.connectionButtonCamera.setEnabled(False)
            self.comboboxCamera.setEnabled(False)

        # Setup the Connections GroupBox
        self.groupConnection = QGroupBox("Connections")

        connectionsLayout = QFormLayout()
        connectionsLayout.setWidget(0, QFormLayout.ItemRole.SpanningRole, QLabel("Serial Port"))
        connectionsLayout.addRow(self.comboboxSerial, self.connectionButtonSerial)
        connectionsLayout.setWidget(2, QFormLayout.ItemRole.SpanningRole, QLabel("Camera"))
        connectionsLayout.addRow(self.comboboxCamera,self.connectionButtonCamera)

        self.groupConnection.setLayout(connectionsLayout)

        # Connect the signals to slots
        self.comboboxSerial.currentIndexChanged.connect(self.selectionSerialChanged)
        self.connectionButtonSerial.toggled.connect(self.onSerialChecked)

        self.comboboxCamera.currentIndexChanged.connect(self.selectionCameraChanged)
        self.connectionButtonCamera.toggled.connect(self.onCameraChecked)
    
    def setupCameraOptions(self):
        # Setup relevant widgets
        labelExposureTime = QLabel("Exposure Time [μs]")
        self.spinboxExposureTime = QDoubleSpinBox()
        self.spinboxExposureTime.setMinimum(10)
        self.spinboxExposureTime.setKeyboardTracking(False)
        self.spinboxExposureTime.setDecimals(0)
        self.spinboxExposureTime.setStepType(QDoubleSpinBox.StepType.AdaptiveDecimalStepType)
        self.sliderExposureTime = QSlider(Qt.Orientation.Horizontal)

        labelGain = QLabel("Gain [dB]")
        self.spinboxGain = QDoubleSpinBox()
        self.spinboxGain.setKeyboardTracking(False)
        self.sliderGain = QSlider(Qt.Orientation.Horizontal)

        labelContrast = QLabel("Contrast")
        self.spinboxContrast = QDoubleSpinBox()
        self.spinboxContrast.setKeyboardTracking(False)
        self.spinboxContrast.setSingleStep(0.01)
        self.sliderContrast = QSlider(Qt.Orientation.Horizontal)
        # self.sliderContrast.setRange(-1.0, 1.0)
        
        # Setup indivisual features layout
        cameraExposureTimeLayout = QHBoxLayout()
        cameraExposureTimeLayout.addWidget(labelExposureTime)
        cameraExposureTimeLayout.addWidget(self.spinboxExposureTime)
        cameraExposureTimeLayout.addWidget(self.sliderExposureTime)

        cameraGainLayout = QHBoxLayout()
        cameraGainLayout.addWidget(labelGain)
        cameraGainLayout.addWidget(self.spinboxGain)
        cameraGainLayout.addWidget(self.sliderGain)

        cameraContrastLayout = QHBoxLayout()
        cameraContrastLayout.addWidget(labelContrast)
        cameraContrastLayout.addWidget(self.spinboxContrast)
        cameraContrastLayout.addWidget(self.sliderContrast)

        # Setup main features layout
        self.groupCameraOptions = QGroupBox("Camera Options")
        mainCameraOptionsLayout = QGridLayout()
        mainCameraOptionsLayout.addLayout(cameraExposureTimeLayout, 0, 0, 1, 2)
        mainCameraOptionsLayout.addLayout(cameraGainLayout, 1, 0, 1, 1)
        mainCameraOptionsLayout.addLayout(cameraContrastLayout, 1, 1, 1, 1)
        self.groupCameraOptions.setLayout(mainCameraOptionsLayout)

        # Connect signals and slots
        self.sliderExposureTime.rangeChanged.connect(self.spinboxExposureTime.setRange)
        self.spinboxExposureTime.valueChanged.connect(self.sliderExposureTime.setValue)
        self.sliderExposureTime.valueChanged.connect(self.spinboxExposureTime.setValue)
        self.spinboxExposureTime.valueChanged.connect(self.setCameraExposureTime)
        # self.sliderExposureTime.valueChanged.connect(self.setCameraExposureTime)

        self.sliderGain.rangeChanged.connect(self.spinboxGain.setRange)
        self.spinboxGain.valueChanged.connect(self.sliderGain.setValue)
        self.sliderGain.valueChanged.connect(self.spinboxGain.setValue)
        self.spinboxGain.valueChanged.connect(self.setCameraGain)
        # self.sliderGain.valueChanged.connect(self.setCameraGain)

        self.sliderContrast.rangeChanged.connect(
            lambda min, max: self.spinboxContrast.setRange(min / 100, max / 100)
        )
        self.spinboxContrast.valueChanged.connect(
            lambda v: self.sliderContrast.setValue(round(v * 100, 0))
        )
        self.sliderContrast.valueChanged.connect(
            lambda v: self.spinboxContrast.setValue(round(v / 100, 2))
        )
        self.spinboxContrast.valueChanged.connect(self.setCameraContrast)
        # self.sliderContrast.valueChanged.connect(self.setCameraContrast)

        self.actionResetCamera = QAction("Reset camera settings", self)
        self.actionResetCamera.setEnabled(False)
        self.actionResetCamera.triggered.connect(
            lambda: self.reset_camera_settings(self.camera)
        )
    
    @Slot()
    def setCameraExposureTime(self, value):
        try:
            self.camera.ExposureTime.SetValue(value)
        except AttributeError:
            logger.debug("Ignored setting the exposure time, no camera connected in the system")

    @Slot()
    def setCameraGain(self, value):
        try:
            self.camera.Gain.SetValue(value)
        except AttributeError:
            logger.debug("Ignored setting the gain, no camera connected in the system")

    @Slot()
    def setCameraContrast(self, value):
        try:
            self.camera.BslContrast.SetValue(value)
        except AttributeError:
            logger.debug("Ignored setting the contrast, no camera connected in the system")

    def setupMinimization(self):
        # Setup the relevant widgets
        self.minimizationButton = QPushButton("Start Minimization", self)
        self.minimizationButton.setCheckable(True)
        self.minimizationButton.setCursor(Qt.CursorShape.PointingHandCursor)

        # Setup the Minimization GroupBox
        self.groupMinimizerOptions = QGroupBox("Minimizer Options")
        self.spinboxInitialPS1 = QDoubleSpinBox()
        self.spinboxInitialPS1.setRange(0.0, 100.0)
        self.spinboxInitialPS1.setSingleStep(0.1)
        self.spinboxInitialPS1.setKeyboardTracking(False)
        self.spinboxInitialPS1.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxInitialPS1": v})
        )
        self.spinboxMinPS1 = QDoubleSpinBox()
        self.spinboxMinPS1.setRange(0.0, 100.0)
        self.spinboxMinPS1.setSingleStep(0.1)
        self.spinboxMaxPS1 = QDoubleSpinBox()
        self.spinboxMaxPS1.setRange(0.0, 100.0)
        self.spinboxMaxPS1.setSingleStep(0.1)

        self.spinboxInitialPS2 = QDoubleSpinBox()
        self.spinboxInitialPS2.setRange(0.0, 100.0)
        self.spinboxInitialPS2.setSingleStep(0.1)
        self.spinboxInitialPS2.setKeyboardTracking(False)
        self.spinboxInitialPS2.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxInitialPS2": v})
        )
        self.spinboxMinPS2 = QDoubleSpinBox()
        self.spinboxMinPS2.setRange(0.0, 100.0)
        self.spinboxMinPS2.setSingleStep(0.1)
        self.spinboxMaxPS2 = QDoubleSpinBox()
        self.spinboxMaxPS2.setRange(0.0, 100.0)
        self.spinboxMaxPS2.setSingleStep(0.1)

        self.spinboxXATol = QSpinBox()
        self.spinboxXATol.setRange(-4, 3)
        self.spinboxXATol.setValue(-4)
        self.spinboxXATol.setPrefix("1E")
        self.spinboxXATol.setKeyboardTracking(False)
        self.spinboxXATol.setToolTip(f"<p>Parameter absolute tolerance</p>")
        self.spinboxXATol.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxXATol": v})
        )

        self.spinboxFATol = QSpinBox()
        self.spinboxFATol.setRange(-1, 14)
        self.spinboxFATol.setValue(-4)
        self.spinboxFATol.setPrefix("1E")
        self.spinboxFATol.setKeyboardTracking(False)
        self.spinboxFATol.setToolTip(f"<p>Objective function absolute tolerance</p>")
        self.spinboxFATol.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxFATol": v})
        )

        self.spinboxMaxIter = QSpinBox()
        self.spinboxMaxIter.setRange(0, 400)
        self.spinboxMaxIter.setValue(100)
        self.spinboxMaxIter.setSpecialValueText("Default")
        self.spinboxMaxIter.setKeyboardTracking(False)
        self.spinboxMaxIter.setToolTip(f"<p>Maximum allowed number of iterations</p>")
        self.spinboxMaxIter.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxMaxIter": v})
        )

        self.spinboxMaxFEval= QSpinBox()
        self.spinboxMaxFEval.setRange(0, 400)
        self.spinboxMaxFEval.setValue(200)
        self.spinboxMaxFEval.setSpecialValueText("Default")
        self.spinboxMaxFEval.setKeyboardTracking(False)
        self.spinboxMaxFEval.setToolTip(f"<p>Maximum allowed number of function evaluations</p>")
        self.spinboxMaxFEval.valueChanged.connect(
            lambda v: self.settings_manager.user_settings.update({"spinboxMaxFEval": v})
        )

        minimizerOptionsPS1Layout = QFormLayout()
        minimizerOptionsPS1Layout.addRow("Initial [A]:", self.spinboxInitialPS1)
        minimizerOptionsPS1Layout.addRow("Min [A]:", self.spinboxMinPS1)
        minimizerOptionsPS1Layout.addRow("Max [A]:", self.spinboxMaxPS1)

        minimizerOptionsPS2Layout = QFormLayout()
        minimizerOptionsPS2Layout.addRow("Initial [A]:", self.spinboxInitialPS2)
        minimizerOptionsPS2Layout.addRow("Min [A]:", self.spinboxMinPS2)
        minimizerOptionsPS2Layout.addRow("Max [A]:", self.spinboxMaxPS2)

        minimizerOtherOptionsLayout = QFormLayout()
        minimizerOtherOptionsLayout.addRow("MAXITER", self.spinboxMaxIter)
        minimizerOtherOptionsLayout.addRow("MAXFEV", self.spinboxMaxFEval)
        minimizerOtherOptionsLayout.addRow("XATOL", self.spinboxXATol)
        minimizerOtherOptionsLayout.addRow("FATOL", self.spinboxFATol)

        mainMinimizerLayout = QVBoxLayout()
        mainMinimizerLayout.addWidget(QLabel("PS1 Settings"), alignment=Qt.AlignmentFlag.AlignCenter)
        mainMinimizerLayout.addLayout(minimizerOptionsPS1Layout)
        mainMinimizerLayout.addSpacing(5)
        mainMinimizerLayout.addWidget(QLabel("PS2 Settings"), alignment=Qt.AlignmentFlag.AlignCenter)
        mainMinimizerLayout.addLayout(minimizerOptionsPS2Layout)
        mainMinimizerLayout.addSpacing(5)
        mainMinimizerLayout.addWidget(QLabel("Other Settings"), alignment=Qt.AlignmentFlag.AlignCenter)
        mainMinimizerLayout.addLayout(minimizerOtherOptionsLayout)
        mainMinimizerLayout.addSpacing(5)
        mainMinimizerLayout.addWidget(self.minimizationButton)
        self.groupMinimizerOptions.setLayout(mainMinimizerLayout)

        # Connect signals to slots
        self.minimizationButton.toggled.connect(self.onMinimizeStateChanged)
        self.spinboxInitialPS1.valueChanged.connect(self.setBounds)
        self.spinboxInitialPS2.valueChanged.connect(self.setBounds)
    
    @Slot(float)
    def setBounds(self, val: float) -> None:
        min, max = self.determineBounds(val)
        if self.sender() is self.spinboxInitialPS1:
            self.spinboxMinPS1.setValue(min)
            self.spinboxMaxPS1.setValue(max)
        if self.sender() is self.spinboxInitialPS2:
            self.spinboxMinPS2.setValue(min)
            self.spinboxMaxPS2.setValue(max)

    def determineBounds(self, val: float) -> tuple[float, float]:
        if 0.0 < val <= 100.0:
            return (val - 0.5, val + 0.5)
        else:
            return (0.0, 0.0)

    def setupMainStatusBar(self):
        self.statusPS1 = QLabel("PS1: -")
        # self.iconConnected = QIcon("autofocus-dev/icons/check-solid.svg")
        # self.iconDisconnected = QIcon("autofocus-dev/icons/xmark-solid.svg")
        # self.statusPS1Connected = QLabel()
        # self.statusPS1Disconnected = QLabel()
        # self.statusPS1Connected.setPixmap(self.iconConnected.pixmap(QSize(15, 15)))
        # self.statusPS1Disconnected.setPixmap(self.iconDisconnected.pixmap(QSize(15, 15)))
        # self.statusPS2Connected = QLabel()
        # self.statusPS2Disconnected = QLabel()
        # self.statusPS2Connected.setPixmap(self.iconConnected.pixmap(QSize(15, 15)))
        # self.statusPS2Disconnected.setPixmap(self.iconDisconnected.pixmap(QSize(15, 15)))
        self.statusPS2 = QLabel("PS2: -")
        self.statusCamera = QLabel("Camera: -")
        # self.statusImProc = QLabel("Img Processing: -")
        # self.statusMinimization = QLabel("Minimizer: -")
        self.mainStatusBar = self.statusBar()
        self.mainStatusBar.setSizeGripEnabled(False)
        self.mainStatusBar.addWidget(self.statusPS1)
        # self.mainStatusBar.addWidget(self.statusPS1Disconnected)
        self.mainStatusBar.addWidget(self.statusPS2)
        # self.mainStatusBar.addWidget(self.statusPS2Connected)
        self.mainStatusBar.addWidget(self.statusCamera)
        # self.mainStatusBar.addWidgget(self.statusPS1Disconnected)
        # self.mainStatusBar.addWidget(self.statusImProc)
        # self.mainStatusBar.addWidget(self.statusMinimization)

    @Slot()
    def continuous_capture(self):
        # Create a camera worker object
        try:
            self.worker = CameraWorkerR(self.camera, self)
        except (pylon.GenericException, AttributeError):
            self.cameraErrorDialog()
        else:
            # Connect signals and slots
            self.worker.handler.updateFrame.connect(self.video_label.setImage)
            self.worker.signals.fps.connect(
                lambda fps: self.statusLabelFPS.setText(f'FPS: {fps:.2f}')
            )
            self.worker.signals.error.connect(self.cameraErrorDialog)
            self.worker.signals.finished.connect(self.onCameraFinished)

            # Final resets
            self.start_button.setEnabled(False)
            self.close_button.setEnabled(True)
            self.close_button.setFocus()
            self.single_button.setEnabled(False)
            self.actionResetCamera.setEnabled(False)
            self.actionSaveImageAs.setEnabled(False)

            # Start the thread
            self.threadpool.start(self.worker)

    @Slot()
    def onCameraFinished(self) -> None:
        self.worker.signals.fps.disconnect()
        self.start_button.setEnabled(True)
        self.start_button.setFocus()
        self.close_button.setEnabled(False)
        self.single_button.setEnabled(True)
        self.video_label.pixmap.setPixmap(QPixmap())
        self.actionResetCamera.setEnabled(True)

    @Slot()
    def cameraErrorDialog(self):
        QMessageBox.critical(
            self,
            "Camera Error",
            "The specified camera could not be started. Check that the camera is properly connected or that the connection has been first established.",
            QMessageBox.StandardButton.Ok
            )

    @Slot()
    def stop_capture(self):
        self.worker.camera.StopGrabbing()
        # self.worker.camera.Close()
        # print("Finished")
        # self.worker.signals.finished.emit()

    @Slot()
    def get_single_image(self):
        # if self.camera is not None and self.camera.IsGrabbing():
        #     self.camera.StopGrabbing()
        try:
            self.temp_img = pylon.PylonImage()
            with self.camera.GrabOne(11000) as grab:
                self.temp_img.AttachGrabResultBuffer(grab)
                # self.temp_img = pylon.PylonImage(grab)
                img = grab.GetArray()
                if img.ndim == 2:
                    h, w = img.shape
                    image = QImage(img.data, w, h, w, QImage.Format.Format_Grayscale8)
                elif self.img.ndim == 3:
                    h, w, ch = self.img.shape
                    image = QImage(img.data, w, h, ch * w, QImage.Format.Format_RGB888)
                self.video_label.setImage(image)
        except (pylon.GenericException, AttributeError):
            self.cameraErrorDialog()
        else:
            self.actionSaveImageAs.setEnabled(True)
    
    @Slot()
    def saveImage(self):
        filename, _ = QFileDialog.getSaveFileName(self, "Save Image", str(BASE_PATH / 'Image.png'), "Image Files (*.png);;All Files (*)")
        if filename:
            if filename.endswith('.png'):
                self.temp_img.Save(pylon.ImageFileFormat_Png, filename)
            else:
                self.temp_img.Save(pylon.ImageFileFormat_Png, filename + '.png')
        self.temp_img.Release()

    @Slot()
    def onROIStateChanged(self):
        if self.roi_checkbox.isChecked():
            self.video_label.roi_draw = True
        else:
            self.video_label.roi_draw = False
        self.settings_manager.user_settings['roi_draw'] = self.video_label.roi_draw
        self.settings_manager.saveUserSettings()

    @Slot()
    def onCrosshairX40StateChanged(self):
        if self.crosshair_x40_checkbox.isChecked():
            self.video_label.draw_crosshair_x40 = True
        else:
            self.video_label.draw_crosshair_x40 = False
        self.settings_manager.user_settings['draw_crosshair_x40'] = self.video_label.draw_crosshair_x40
        self.settings_manager.saveUserSettings()

    @Slot()
    def onCrosshairX16StateChanged(self):
        if self.crosshair_x16_checkbox.isChecked():
            self.video_label.draw_crosshair_x16 = True
        else:
            self.video_label.draw_crosshair_x16 = False
        self.settings_manager.user_settings['draw_crosshair_x16'] = self.video_label.draw_crosshair_x16
        self.settings_manager.saveUserSettings()

    @Slot()
    def onScanX40StateChanged(self):
        if self.scan_x40_checkbox.isChecked():
            self.video_label.draw_scan_x40 = True
        else:
            self.video_label.draw_scan_x40 = False
        self.settings_manager.user_settings['draw_scan_x40'] = self.video_label.draw_scan_x40
        self.settings_manager.saveUserSettings()

    @Slot()
    def onScanX16StateChanged(self):
        if self.scan_x16_checkbox.isChecked():
            self.video_label.draw_scan_x16 = True
        else:
            self.video_label.draw_scan_x16 = False
        self.settings_manager.user_settings['draw_scan_x16'] = self.video_label.draw_scan_x16
        self.settings_manager.saveUserSettings()

    @Slot()
    def onGaussianFilterStateChanged(self):
        if self.checkboxGaussianFiltering.isChecked():
            self.spinboxGaussianKernel.setEnabled(True)
        else:
            self.spinboxGaussianKernel.setEnabled(False)

    @Slot()
    def onImprocStateChanged(self, checked):
        if checked:
            if self.start_button.isEnabled():
                self.improc_button.setChecked(False)
                self.imageProcessingErrorDialog()
            else:
                self.imageProcessingWorker = ImageProcessing(self)

                # Connect the signal from the camera worker directly to the image processing function
                self.worker.handler.progress.connect(self.imageProcessingWorker.imageProcessing)
                self.spinboxImagesToAccumulate.valueChanged.connect(self.imageProcessingWorker.setNumberOfImagesToAccumulate)
                self.spinboxGaussianKernel.valueChanged.connect(self.imageProcessingWorker.setGaussianKernel)
                self.spinboxThreshold.valueChanged.connect(self.imageProcessingWorker.setThreshold)

                self.imageProcessingWorker.signals.imageProcessingDone.connect(self.imageProcessingFeed.video_label.setImage)
                self.imageProcessingWorker.signals.imageProcessingEllipse.connect(self.plotting.updatePlotEllipseAxes)
                self.imageProcessingWorker.signals.imageProcessingHist.connect(self.histograms.updateHist)
                self.imageProcessingWorker.signals.imageProcessingHor.connect(self.histograms.updateHistHor)
                self.imageProcessingWorker.signals.imageProcessingVert.connect(self.histograms.updateHistVert)
                self.threadpool.start(self.imageProcessingWorker)
        else:
            if hasattr(self, 'worker') and hasattr(self, 'imageProcessingWorker'):
                if self.imageProcessingWorker.eventloop.isRunning():
                    self.worker.handler.progress.disconnect(self.imageProcessingWorker.imageProcessing)
                    self.imageProcessingWorker.eventloop.exit()

    def imageProcessingErrorDialog(self):
        QMessageBox.critical(
            self,
            "Image Processing Error",
            f"<p><b><font size='+1'>Image processing could not be started.</font></b></p>"
            f"<p>The camera needs to be opened first in order for image processing to start.</p>",
            QMessageBox.StandardButton.Ok
        )

    @Slot()
    def initializeMinimization(self):
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.minimizerWorker = Minimizer(self.pscontroller, self.mutex, self.condition, self)
        self.imageProcessingWorker.signals.imageProcessingEllipse.connect(self.minimizerWorker.get_res)
        self.minimizerWorker.signals.boundsError.connect(self.minimizerBoundsError)
        self.minimizerWorker.signals.inAccumulation.connect(self.imageProcessingWorker.setInAccumulation)
        self.minimizerWorker.signals.updateCurrent.connect(self.plotting.updatePlotCurrents)
        self.minimizerWorker.signals.setCurrent.connect(self.setPSCurrents)
        self.minimizerWorker.signals.updateFunction.connect(self.plotting.updatePlotFunction)
        self.minimizerWorker.signals.finished.connect(
            lambda: self.improc_button.setChecked(False)
        )
        self.minimizerWorker.signals.finished.connect(
            lambda: self.minimizationButton.setChecked(False)
        )
        self.minimizerWorker.signals.finished.connect(self.minimizerFinished)

    def startMinimization(self):
        if not self.start_button.isEnabled() and self.connectionButtonSerial.isChecked():
            if not self.improc_button.isChecked():
                self.improc_button.setChecked(True)
            self.initializeMinimization()
            self.threadpool.start(self.minimizerWorker)
            self.minimizationButton.setText("Stop Minimization")
        else:
            self.minimizationButton.setChecked(False)
            self.minimizerStartErrorDialog()

    @Slot()
    def onMinimizeStateChanged(self, checked):
        if checked:
            if self.plotting.data.major:
                result = QMessageBox.warning(
                self,
                "Found existing data",
                f"<p><b><font size='+1'>Data from a previous run were found.</font size='+1'></b></p>"
                f"</p>The minimization process will <b>override</b> any existing data. This cannot be undone. Continue?</p>",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
                )
                if result == QMessageBox.StandardButton.Yes:
                    self.plotting.actionClearData.trigger()
                    self.startMinimization()
                else:
                    self.minimizationButton.setChecked(False)
            else:
                self.startMinimization()
        else:
            if hasattr(self, 'minimizerWorker'):
                self.minimizerWorker.control = True
            self.minimizationButton.setText("Start Minimization")
    
    @Slot()
    def minimizerFinished(self):
        if self.minimizerWorker.solution is not None:
            status = self.minimizerWorker.solution.status
            if status == 99:
                reason = "Ended manually by user."
            else:
                reason = self.minimizerWorker.solution.message
            iterations = self.minimizerWorker.solution.nit
            evaluations = self.minimizerWorker.solution.nfev
            sol = self.minimizerWorker.solution.x
        
            result = QMessageBox.information(
                self,
                "Minimization finished",
                f"<p><b><font size='+1'>The minimization process finished.</font size='+1'></b></p>"
                f"<p>Reason: {reason}<br>"
                f"Iterations: {iterations}<br>"
                f"Function evaluations: {evaluations}<br>"
                f"Result: Q1 = {sol[0]:.4f} A, Q2/3 = {sol[1]:.4f} A</p>"
                f"<p>Save current data?</p>",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )

            if result == QMessageBox.StandardButton.Yes:
                # self.plotting.actionSaveData.trigger()
                self.plotting.onActionSaveData(self.imageProcessingWorker.image_data_path.parent)

    @Slot()
    def minimizerBoundsError(self):
        QMessageBox.critical(
            self,
            "Minimizer Error",
            f"<p><b><font size='+1'>Minimization bounds are incorrect.</font></b></p>"
            f"<p>An upper bound is less than the corresponding lower bound.</p>",
            QMessageBox.StandardButton.Ok
        )
    
    @Slot()
    def minimizerStartErrorDialog(self):
        QMessageBox.critical(
            self,
            "Minimizer Error",
            f"<p><b><font size='+1'>The minimizer could not be started.</font></b></p>"
            f"<p>Verify that the camera is properly connected and acquiring images (Start button is pressed) and that the power supplies are successfully connected.</p>",
            QMessageBox.StandardButton.Ok
        )

    @Slot(QPoint)
    def onPositionChanged(self, p):
        self.statusLabelPosition.setText(f'(y={p.y()}, x={p.x()})')

    # TODO This could be removed, it is kept for logging purposes
    @Slot()
    def selectionSerialChanged(self):
        logger.debug(
            f'Serial port selection changed.\n'
            f'index: {self.comboboxSerial.currentIndex()}\n'
            f'port: {self.comboboxSerial.currentText()}\n'
            f'name: {self.ports[self.comboboxSerial.currentIndex()].name}\n'
        )

    # TODO This could be removed, it is kept for logging purposes
    @Slot()
    def selectionCameraChanged(self):
        logger.debug(
            f'Camera selection changed.\n'
            f'index: {self.comboboxCamera.currentIndex()}\n'
            f'camera: {self.comboboxCamera.currentText()}\n'
        )

    @Slot()
    def onSerialChecked(self, checked):
        if checked:
            self.serial_port = self.connect_port(self.ports[self.comboboxSerial.currentIndex()].name)
            self.pscontroller = PSController(self.serial_port, self)
            self.pscontroller.signals.updateValues.connect(self.updateGUI)
            self.comboboxSerial.setEnabled(False)
            self.connectionButtonSerial.setText("Disconnect")
            # print(self.pscontroller.ps1.get_power_status())
            # 
            # print(self.pscontroller.ps2.get_power_status())
            # 
            # self.psLCD1.currentDial.valueChanged.connect(self.onDial1Moved)
            self.pscontroller.signals.terminate.connect(
                lambda : self.connectionButtonSerial.setChecked(False)
            )
            self.pscontroller.signals.terminate.connect(
                lambda: self.disconnect_port(self.serial_port)
            )
            self.threadpool.start(self.pscontroller)
            self.pscontroller.signals.serialConnectionSuccessful.connect(self.onSerialConnectionSuccess)
            self.psLCD1.currentDial.valueChanged.connect(self.pscontroller.setPS1Current)
            self.psLCD2.currentDial.valueChanged.connect(self.pscontroller.setPS2Current)
        else:
            # if self.ps1.get_power_status() == "ON" or self.ps2.get_power_status() == "ON":
            # print(self.pscontroller.ps2.set_power_status("OFF"))
            self.statusPS1.setText("PS1: OFF")
            # print(self.pscontroller.ps1.set_power_status("OFF"))
            self.statusPS2.setText("PS1: OFF")
            self.comboboxSerial.setEnabled(True)
            self.connectionButtonSerial.setText("Connect")
            if all(self.pscontroller.successfull.values()):
                self.pscontroller.control = False
                self.pscontroller.loop.exit() # Implement a signal to tell the internal loop to terminate
            self.psLCD1.currentDial.valueChanged.disconnect(self.pscontroller.setPS1Current)
            self.psLCD2.currentDial.valueChanged.disconnect(self.pscontroller.setPS2Current)

    @Slot(dict) 
    def updateGUI(self, data):
        self.psLCD1.voltageLCD.display(data['MV1'])
        self.psLCD1.currentLCD.display(data['MC1'])
        self.psLCD2.voltageLCD.display(data['MV2'])
        self.psLCD2.currentLCD.display(data['MC2'])
    
    @Slot(bool)
    def onSerialConnectionSuccess(self, success):
        if success:
            self.psLCD1.setEnabled(True)
            self.statusPS1.setText("PS1: ON")
            self.psLCD2.setEnabled(True)
            self.statusPS2.setText("PS1: ON")
        else:
            self.serialConnectionFailedDialog()
    
    def serialConnectionFailedDialog(self):
        QMessageBox.critical(
            self,
            "Serial Connection Error",
            f"<p><b><font size='+1'>Failed to connect with the power supplies.</font></b></p>"
            f"<p>The following might help to determine which caused the failure:<br>"
            f"PS1 (Q1) connected: <b>{self.pscontroller.successfull['PS1']}</b><br>"
            f"PS2 (Q2/3) connected: <b>{self.pscontroller.successfull['PS2']}</b></p>"
            f"<p>Check whether they are properly connected to the computer or to external power.</p>",
            QMessageBox.StandardButton.Ok
        )
    # @Slot(int)
    # def onDial1Moved(self, value):
    #     print(f'Current of PS1 changed to: {value / 100}')
    #     self.ps1.set_programmed_current(value / 100)
    #     # print("Restarted refresh timer.")
    #     # self.refreshTimer.start(1000)

    # @Slot(int)
    # def onDial2Moved(self, value):
    #     print(f'Current of PS2 changed to: {value / 100}')
    #     self.ps2.set_programmed_current(value / 100)
    #     # print("Restarted refresh timer.")
    #     # self.refreshTimer.start(1000)

    @Slot(list)
    def setPSCurrents(self, x):
        logger.info(f'Setting Q1 current to: {x[0]}')
        self.pscontroller.setPS1Current(x[0] * 100)
        logger.info(f'Setting Q2/3 currents to: {x[1]}')
        self.pscontroller.setPS2Current(x[1] * 100)

    @Slot()
    def onCameraChecked(self, checked):
        if checked:
            try:
                self.camera = self.connect_camera(self.comboboxCamera.currentIndex())
            except pylon.RuntimeException:
                self.connectionButtonCamera.setChecked(False)
                logger.error("Could not connect to camera")
                QMessageBox.critical(
                self,
                "Camera Error",
                "Establishing connection with the camera failed. Check that the camera is not open in another software.",
                QMessageBox.StandardButton.Ok
                )
            else:
                self.comboboxCamera.setEnabled(False)
                self.connectionButtonCamera.setText("Disconnect")
                self.configure_camera(self.camera)

                self.updateCameraParameters()
                self.actionResetCamera.setEnabled(True)
        else:
            if self.camera is not None:
                if self.camera.IsGrabbing():
                    self.stop_capture()
                self.disconnect_camera(self.camera)
                self.comboboxCamera.setEnabled(True)
                self.connectionButtonCamera.setText("Connect")
                self.actionResetCamera.setEnabled(False)

    def configure_camera(self, camera):
        camera.Open()
        # to get consistant results it is always good to start from "power-on" state
        # camera.UserSetSelector.Value = "Default"
        # camera.UserSetLoad.Execute()

        # Configure the camera
        camera.PixelFormat.Value = "Mono8"
        # camera.ExposureTime.Value = 50_000.0
        # camera.Gain.Value = 25.0
        # camera.BslContrast.Value = 0.0
        self.camera_width = camera.Width.GetValue()
        self.camera_height = camera.Height.GetValue()
        self.event_filter.setCameraWidthAndHeight((self.camera_width, self.camera_height))
    
    def updateCameraParameters(self):
        self.sliderExposureTime.setRange(
            self.camera.ExposureTime.Min,
            self.camera.ExposureTime.Max
        )
        # self.camera.ExposureTime.SetValue(30_000.0)
        self.spinboxExposureTime.setValue(self.camera.ExposureTime.GetValue())

        self.sliderGain.setRange(
            self.camera.Gain.Min,
            self.camera.Gain.Max
        )
        self.spinboxGain.setValue(self.camera.Gain.GetValue())

        self.sliderContrast.setRange(
            self.camera.BslContrast.Min * 100,
            self.camera.BslContrast.Max * 100
        )
        self.spinboxContrast.setValue(self.camera.BslContrast.GetValue())
    
    @Slot()
    def reset_camera_settings(self, camera):
        if camera.IsOpen():
            if camera.IsGrabbing():
                camera.StopGrabbing()

            # Retrieve default settings
            camera.UserSetSelector.SetValue("Default")
            camera.UserSetLoad.Execute()

            # Re-configure the camera
            camera.PixelFormat.SetValue("Mono8")
            self.camera_width = camera.Width.GetValue()
            self.camera_height = camera.Height.GetValue()
            self.event_filter.setCameraWidthAndHeight((self.camera_width, self.camera_height))
            self.updateCameraParameters()

    def closeEvent(self, event):
        result = QMessageBox.question(
            self,
            "Confirm Exit",
            "Are you sure you want to quit?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if result == QMessageBox.StandardButton.Yes:
            if self.connectionButtonSerial.isChecked():
                # self.connectionButtonSerial.setChecked(False)
                if self.pscontroller.queue_thread.is_alive():
                    self.pscontroller.control = False
                    self.pscontroller.loop.exit()
                    self.pscontroller.queue_thread.join(timeout=0.5)
            if self.camera is not None:
                if self.camera.IsGrabbing():
                    logger.warning("Camera is still open")
                    self.stop_capture()
                    logger.info("Camera closed")
            if hasattr(self, 'imageProcessingWorker'):
                if self.imageProcessingWorker.eventloop.isRunning():
                    logger.warning("Image processing is still running")
                    self.imageProcessingWorker.eventloop.exit()

            event.accept()
        else:
            event.ignore()

def main() -> int:
    app = QApplication([])
    app.setStyle('Fusion')
    app.setWheelScrollLines(1)
    app.setStyleSheet(CUSTOM_STYLESHEET)

    logger.info("μFocus application started")

    widget = MainWindow()
    
    available_geometry = widget.screen().availableGeometry()
    widget.resize(int(0.66 * available_geometry.width()), int(0.85 * available_geometry.height()))
    widget.show()

    exit_code = app.exec()
    logger.info("μFocus application terminated")
    
    return exit_code
    