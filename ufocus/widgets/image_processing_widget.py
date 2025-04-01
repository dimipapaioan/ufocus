from numpy import ndarray
from PySide6.QtCore import (
    Qt,
    Slot,
    QSize,
)
from PySide6.QtGui import (
    QImage,
    QPixmap,
    QAction,
    QIcon,
)
from PySide6.QtWidgets import (
    QWidget,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QToolBar,
    QFormLayout,
    QHBoxLayout,
)

from .floating_widget import FloatingWidget
from image_processing import DetectedEllipse
from minimizer import PSCurrentsInfo, ObjectiveFunctionInfo
import resources  # noqa: F401


class ImageProcessingQLabel(QLabel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setMinimumSize(640, 480)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding
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

        self.setPixmap(
            QPixmap.fromImage(image).scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio
            )
        )

    def sizeHint(self) -> QSize:
        return QSize(640, 480)


class ImageProcessingWidget(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.imageProcessingWindow = None
        self.video_label = ImageProcessingQLabel(self)

        self.actionOpenInWindow = QAction("Open in window", self)
        self.actionOpenInWindow.setIcon(
            QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg"))
        )
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
        formObjFuncStats.addRow(
            "{:<16}".format("Last obj. func.:"), self.obj_func_previous_label
        )
        formObjFuncStats.addRow(
            "{:<16}".format("Min. obj. func.:"), self.obj_func_min_label
        )
        formObjFuncStats.addRow(
            "{:<16}".format("Last delta:"), self.obj_func_delta_label
        )
        formObjFuncStats.addRow(
            "{:<16}".format("Min. delta:"), self.obj_func_min_delta_label
        )

        self.ellipse_major_label = QLabel("nan")
        self.ellipse_minor_label = QLabel("nan")
        self.ellipse_area_label = QLabel("nan")
        self.ellipse_circ_label = QLabel("nan")

        ellipseStats = QFormLayout()
        ellipseStats.addRow("{:<12}".format("Major:"), self.ellipse_major_label)
        ellipseStats.addRow("{:<12}".format("Minor:"), self.ellipse_minor_label)
        ellipseStats.addRow("{:<12}".format("Area:"), self.ellipse_area_label)
        ellipseStats.addRow("{:<12}".format("Circularity:"), self.ellipse_circ_label)

        imgProcFeedLiveStats = QHBoxLayout()
        imgProcFeedLiveStats.addLayout(ellipseStats)
        imgProcFeedLiveStats.addLayout(formPSCurrentsStats)
        imgProcFeedLiveStats.addLayout(formObjFuncStats)

        layout = QVBoxLayout()
        layout.addWidget(self.toolbar)
        layout.addWidget(self.video_label)
        layout.addLayout(imgProcFeedLiveStats)
        self.setLayout(layout)

    @Slot()
    def onActionOpenWindowClicked(self, checked):
        if checked:
            self.imageProcessingWindow = FloatingWidget("Processed Feed", self)
            self.actionOpenInWindow.setIcon(
                QIcon(QPixmap(":/icons/arrow-right-to-bracket-solid.svg"))
            )
            self.actionOpenInWindow.setText("Return to main window")
        else:
            self.actionOpenInWindow.setIcon(
                QIcon(QPixmap(":/icons/arrow-right-from-bracket-solid.svg"))
            )
            self.imageProcessingWindow.close()
            self.actionOpenInWindow.setText("Open in window")
            self.imageProcessingWindow = None

    @Slot(PSCurrentsInfo, ObjectiveFunctionInfo)
    def onMinimizerFuncEvalUpdate(
        self, ps_currents: PSCurrentsInfo, obj_func: ObjectiveFunctionInfo
    ) -> None:
        self.ps1_previous_label.setText(f"{ps_currents.ps1_previous:.4f}")
        self.ps2_previous_label.setText(f"{ps_currents.ps2_previous:.4f}")
        self.ps1_min_label.setText(f"{ps_currents.ps1_min:.4f}")
        self.ps2_min_label.setText(f"{ps_currents.ps2_min:.4f}")
        self.obj_func_previous_label.setText(f"{obj_func.previous:.4f}")
        self.obj_func_min_label.setText(f"{obj_func.min_val:.4f}")
        self.obj_func_delta_label.setText(f"{obj_func.delta:.4f}")
        self.obj_func_min_delta_label.setText(f"{obj_func.min_delta:.4f}")

    @Slot(DetectedEllipse)
    def onImageProcessingEllipsisUpdate(self, ellipse: DetectedEllipse) -> None:
        self.ellipse_major_label.setText(f"{ellipse.major:.4f}")
        self.ellipse_minor_label.setText(f"{ellipse.minor:.4f}")
        self.ellipse_area_label.setText(f"{ellipse.area:.4f}")
        self.ellipse_circ_label.setText(f"{ellipse.circularity:.4f}")
