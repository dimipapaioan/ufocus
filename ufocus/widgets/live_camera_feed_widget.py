from PySide6.QtCore import Qt, Slot, QSize, QRectF, QPoint
from PySide6.QtGui import QImage, QColor, QPixmap, QPainter, QPen, QPolygon
from PySide6.QtWidgets import (
    QSizePolicy,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
)

import resources  # noqa: F401


class LiveCameraFeedWidget(QGraphicsView):
    def __init__(self, parent=None) -> None:
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
            QSizePolicy.Policy.MinimumExpanding, QSizePolicy.Policy.MinimumExpanding
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
        self.pixmap.setPixmap(
            self.drawRegions(QPixmap.fromImage(image)).scaled(
                self.viewport().size(), Qt.AspectRatioMode.KeepAspectRatio
            )
        )
        self.pixmap.setPos(
            self.scene().sceneRect().center() - self.pixmap.boundingRect().center()
        )

    def drawRegions(self, pixmap: QPixmap) -> QPixmap:
        if (
            self.roi_draw
            or self.draw_crosshair_x40
            or self.draw_crosshair_x16
            or self.draw_scan_x40
            or self.draw_scan_x16
        ):
            with QPainter(pixmap) as painter:
                if self.pen_width is None or self.font_width is None:
                    self.pen_width = round(self.parent.camera.width * 0.004)
                    self.font_width = round(self.parent.camera.width * 0.015)
                painter.setRenderHints(
                    QPainter.RenderHint.Antialiasing
                    | QPainter.RenderHint.TextAntialiasing
                )
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
        painter.drawRect(
            self.p_i.x(),
            self.p_i.y(),
            self.p_f.x() - self.p_i.x(),
            self.p_f.y() - self.p_i.y(),
        )
        painter.drawText(
            self.p_i.x() + 1.5 * self.pen_width, self.p_i.y() - self.font_width, "ROI"
        )

    def drawCrosshairX40(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor(255, 0, 255))
        painter.setPen(pen)
        painter.drawLine(
            0, self.p_cross_x40.y(), self.parent.camera.width, self.p_cross_x40.y()
        )
        painter.drawLine(
            self.p_cross_x40.x(), 0, self.p_cross_x40.x(), self.parent.camera.height
        )
        painter.drawText(
            self.p_cross_x40.x() + 1.5 * self.pen_width, self.font_width + 5, "x40"
        )

    def drawCrosshairX16(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor(255, 0, 0))
        painter.setPen(pen)
        painter.drawLine(
            0, self.p_cross_x16.y(), self.parent.camera.width, self.p_cross_x16.y()
        )
        painter.drawLine(
            self.p_cross_x16.x(), 0, self.p_cross_x16.x(), self.parent.camera.height
        )
        painter.drawText(
            self.p_cross_x16.x() + 1.5 * self.pen_width, self.font_width + 5, "x16"
        )

    def drawScanRegionX40(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor(255, 255, 0))
        painter.setPen(pen)
        if len(self.pts_scan_x40) < 4:
            painter.drawPoints(self.pts_scan_x40)
        else:
            polygon = QPolygon(self.pts_scan_x40)
            painter.drawPolygon(polygon)
            painter.drawText(
                polygon.boundingRect().topLeft()
                + QPoint(2 * self.pen_width, -self.font_width),
                "Scan x40",
            )

    def drawScanRegionX16(self, painter: QPainter, pen: QPen) -> None:
        pen.setColor(QColor("orange"))
        painter.setPen(pen)
        if len(self.pts_scan_x16) < 4:
            painter.drawPoints(self.pts_scan_x16)
        else:
            polygon = QPolygon(self.pts_scan_x16)
            painter.drawPolygon(self.pts_scan_x16)
            painter.drawText(
                polygon.boundingRect().topLeft()
                + QPoint(2 * self.pen_width, -self.font_width),
                "Scan x16",
            )

    def resizeEvent(self, event) -> None:
        self.scene().setSceneRect(self.scene().itemsBoundingRect())
        super().resizeEvent(event)

    def sizeHint(self) -> QSize:
        return QSize(642, 482)
