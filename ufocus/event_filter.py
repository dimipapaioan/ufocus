# -*- coding: utf-8 -*-

from PySide6.QtCore import (
    Qt, QObject, Signal, QPoint, QPointF
    )
from PySide6.QtWidgets import QGraphicsSceneMouseEvent

class EventFilter(QObject):
    
    positionChanged = Signal(QPoint)
    
    def __init__(self, widget):
        super().__init__(widget)
        self.widget = widget
        self.camera_width = 2448
        self.camera_height = 2048
        self.widget.scene().installEventFilter(self)
        self.widget.setMouseTracking(True)

    def eventFilter(self, obj, event: QGraphicsSceneMouseEvent):
        if obj is self.widget.scene() and not self.widget.pixmap.pixmap().isNull():
            if event.type() == QGraphicsSceneMouseEvent.Type.GraphicsSceneMousePress:
                self.height = self.widget.pixmap.sceneBoundingRect().height()
                self.width = self.widget.pixmap.sceneBoundingRect().width()
                
                # Correct the position of the event
                position = self.correctPosition(event)

                if event.button() == Qt.MouseButton.LeftButton:
                    if self.widget.pixmap.sceneBoundingRect().contains(event.scenePos()):
                        self.ratio_width = self.camera_width / self.width
                        self.ratio_height = self.camera_height / self.height

                        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                            # self.crosshairPoint.emit(position.toPoint() * self.ratio_height)
                            if self.widget.p_cross_x40 is None:
                                self.widget.p_cross_x40 = position.toPoint() * self.ratio_height
                                self.widget.parent.settings_manager.user_settings['p_cross_x40'] = self.widget.p_cross_x40
                                self.widget.parent.settings_manager.saveUserSettings()
                            else:
                                event.ignore()

                        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
                            if len(self.widget.pts_scan_x40) < 4:
                                self.widget.pts_scan_x40.append(position.toPoint() * self.ratio_height)
                                self.widget.parent.settings_manager.user_settings['pts_scan_x40'] = self.widget.pts_scan_x40
                                self.widget.parent.settings_manager.saveUserSettings()
                            else:
                                event.ignore()

                        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                            # self.crosshairPoint.emit(position.toPoint() * self.ratio_height)
                            if self.widget.p_cross_x16 is None:
                                self.widget.p_cross_x16 = position.toPoint() * self.ratio_height
                                self.widget.parent.settings_manager.user_settings['p_cross_x16'] = self.widget.p_cross_x16
                                self.widget.parent.settings_manager.saveUserSettings()
                            else:
                                event.ignore()

                        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.AltModifier):
                            if len(self.widget.pts_scan_x16) < 4:
                                self.widget.pts_scan_x16.append(position.toPoint() * self.ratio_height)
                                self.widget.parent.settings_manager.user_settings['pts_scan_x16'] = self.widget.pts_scan_x16
                                self.widget.parent.settings_manager.saveUserSettings()
                            else:
                                event.ignore()

                        if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                            if self.widget.roi == False:
                                self.widget.drawing = True
                                self.widget.p_i = position.toPoint() * self.ratio_height
                                # self.widget.p_i = QPoint(
                                #     position.toPoint().x() * self.ratio_width, 
                                #     position.toPoint().y() * self.ratio_height
                                # )
                                # print(f'clicked, {self.widget.p_i}, {self.widget.p_f}')

                if event.button() == Qt.MouseButton.MiddleButton:
                    if self.widget.pixmap.sceneBoundingRect().contains(event.scenePos()):
                        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                            self.widget.p_cross_x40 = None
                            self.widget.parent.settings_manager.user_settings['p_cross_x40'] = self.widget.p_cross_x40
                            self.widget.parent.settings_manager.saveUserSettings()

                        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier):
                            self.widget.pts_scan_x40.clear()
                            self.widget.parent.settings_manager.user_settings['pts_scan_x40'] = self.widget.pts_scan_x40
                            self.widget.parent.settings_manager.saveUserSettings()

                        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
                            self.widget.p_cross_x16 = None
                            self.widget.parent.settings_manager.user_settings['p_cross_x16'] = self.widget.p_cross_x16
                            self.widget.parent.settings_manager.saveUserSettings()

                        if event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.AltModifier):
                            self.widget.pts_scan_x16.clear()
                            self.widget.parent.settings_manager.user_settings['pts_scan_x16'] = self.widget.pts_scan_x16
                            self.widget.parent.settings_manager.saveUserSettings()

                        if event.modifiers() == Qt.KeyboardModifier.NoModifier:
                            self.widget.p_i = None
                            self.widget.parent.settings_manager.user_settings['p_i'] = self.widget.p_i
                            self.widget.p_f = None
                            self.widget.parent.settings_manager.user_settings['p_f'] = self.widget.p_f
                            self.widget.roi = False
                            self.widget.parent.settings_manager.user_settings['roi'] = self.widget.roi
                            self.widget.parent.settings_manager.saveUserSettings()
                    # print(f'clicked, {self.p_i}, {self.p_f}')

            if event.type() == QGraphicsSceneMouseEvent.Type.GraphicsSceneMouseMove and self.widget.drawing == True:
                # Correct the position of the event
                position = self.correctPosition(event)

                if self.widget.pixmap.sceneBoundingRect().contains(event.scenePos()):
                    self.widget.p_f = position.toPoint() * self.ratio_height
                    # print(f'moved, {self.p_i}, {self.p_f}')
                    # self.positionChanged.emit(position.toPoint() * self.ratio_height)
                    self.positionChanged.emit(
                        QPoint(
                            position.toPoint().x() * self.ratio_width, 
                            position.toPoint().y() * self.ratio_height
                        )
                    )
                # else:
                #     print(f'moved outside, {self.p_i}, {self.p_f}')
            
            # The following code can be used with self.widget.setMouseTracking(True)
            if event.type() == QGraphicsSceneMouseEvent.Type.GraphicsSceneMouseMove:
                # Correct the position of the event
                position = self.correctPosition(event)

                if self.widget.pixmap.sceneBoundingRect().contains(event.scenePos()):
                    # self.positionChanged.emit(position.toPoint() * self.camera_height / self.widget.pixmap.pixmap().size().height())
                    self.positionChanged.emit(
                        QPoint(
                            position.toPoint().x() * self.camera_width / self.widget.pixmap.pixmap().size().width(), 
                            position.toPoint().y() * self.camera_height / self.widget.pixmap.pixmap().size().height()
                        )
                    )

            if event.type() == QGraphicsSceneMouseEvent.Type.GraphicsSceneMouseRelease:
                # Correct the position of the event
                position = self.correctPosition(event)

                if event.button() == Qt.MouseButton.LeftButton and self.widget.roi == False and self.widget.drawing == True:
                    self.widget.drawing = False
                    self.widget.roi = True
                    self.widget.parent.settings_manager.user_settings['roi'] = self.widget.roi
                    if self.widget.pixmap.sceneBoundingRect().contains(event.scenePos()):
                        self.widget.p_f = position.toPoint() * self.ratio_height
                        self.widget.parent.settings_manager.user_settings['p_i'] = self.widget.p_i
                        self.widget.parent.settings_manager.user_settings['p_f'] = self.widget.p_f
                        # self.widget.roi = True
                        # print(f'roi, {self.p_i}, {self.p_f}')
                    # else:
                    #     print(f'roi, {self.p_i}, {self.p_f}')
                    self.widget.parent.settings_manager.saveUserSettings()
                
        return super().eventFilter(obj, event)
    
    def correctPosition(self, event: QGraphicsSceneMouseEvent) -> QPointF:
        return event.scenePos() - (self.widget.scene().sceneRect().center() - self.widget.pixmap.boundingRect().center())

    def setCameraWidthAndHeight(self, value):
        self.camera_width, self.camera_height = value