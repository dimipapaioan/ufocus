# -*- coding: utf-8 -*-

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    Qt,
    Signal,
)
from PySide6.QtGui import (
    QMouseEvent,
)


class EventFilterCal(QObject):
    
    positionChanged = Signal(QPoint)
    
    def __init__(self, widget):
        super().__init__(widget)
        self.widget = widget
        self.widget.installEventFilter(self)
        # self.widget.setMouseTracking(True)
        self.p1 = None
        self.p2 = None
        self.p3 = None
        self.p4 = None
        self.p5 = None

    def eventFilter(self, obj, event: QEvent):
        if obj is self.widget and self.widget.pixmap is not None:
            if event.type() == QEvent.Type.MouseButtonPress:
                mouse_event = QMouseEvent(event)
                self.height = self.widget.pixmap.size().height()
                self.width = self.widget.pixmap.size().width()

                # Correct the position of the event
                position = self.correctPosition(mouse_event)

                if mouse_event.button() == Qt.MouseButton.LeftButton:
                    if self.widget.pixmap.rect().contains(position.toPoint()):
                        self.ratio_width = 2448.0 / self.width
                        self.ratio_height = 2048.0 / self.height

                        if self.p1 is None:
                            self.p1 = position.toPoint() * self.ratio_height
                            # self.p1 = QPoint(
                            #     position.toPoint().x() * self.ratio_width, 
                            #     position.toPoint().y() * self.ratio_height
                            # )
                            self.widget.parent.drawPoint(position.toPoint(), self.widget.pixmap)
                        elif self.p2 is None:
                            self.p2 = position.toPoint() * self.ratio_height
                            self.widget.parent.drawPoint(position.toPoint(), self.widget.pixmap)
                        elif self.p3 is None:
                            self.p3 = position.toPoint() * self.ratio_height
                            self.widget.parent.drawPoint(position.toPoint(), self.widget.pixmap)
                        elif self.p4 is None:
                            self.p4 = position.toPoint() * self.ratio_height
                            self.widget.parent.drawPoint(position.toPoint(), self.widget.pixmap)
                        elif self.p5 is None:
                            self.p5 = position.toPoint() * self.ratio_height
                            self.widget.parent.drawPoint(position.toPoint(), self.widget.pixmap)

                if mouse_event.button() == Qt.MouseButton.MiddleButton:
                    if obj.pixmap.rect().contains(position.toPoint()):
                        self.p1 = None
                        self.p2 = None
                        self.p3 = None
                        self.p4 = None
                        self.p5 = None
                        self.widget.setImage(self.widget.parent.im)

                print(f'Click: {self.p1}, {self.p2}, {self.p3}, {self.p4}, {self.p5}')
            
            if event.type() == QEvent.Type.MouseMove:
                # Correct the position of the event
                position = self.correctPosition(event)

                if self.widget.pixmap.rect().contains(position.toPoint()):
                    # self.positionChanged.emit(position.toPoint() * 2048.0 / self.widget.pixmap.size().height())
                    # self.positionChanged.emit(
                    #     QPoint(
                    #         position.toPoint().x() * 2448.0 / self.widget.pixmap.size().width(), 
                    #         position.toPoint().y() * 2048.0 / self.widget.pixmap.size().height()
                    #     )
                    # )
                    print(position.toPoint() * 2048.0 / self.widget.pixmap.size().height())
                
        return super().eventFilter(obj, event)
    
    def correctPosition(self, event):
        return event.position() - (self.widget.contentsRect().center() - self.widget.pixmap.rect().center())
    
    # The following code can be used to single out events like Ctrl + Click or Ctrl + Shift + Click
    # if mouse_event.button() == Qt.MouseButton.LeftButton:
    #                 # Correct the position of the event
    #                 position = self.correctPosition(mouse_event)

    #                 if self.widget.pixmap.rect().contains(position.toPoint()):
    #                     self.ratio_width = 2448.0 / self.width
    #                     self.ratio_height = 2048.0 / self.height

    #                     if mouse_event.modifiers() == Qt.KeyboardModifier.ControlModifier:
    #                         self.p1 = position.toPoint() * self.ratio_height
    #                         # self.p1 = QPoint(
    #                         #     position.toPoint().x() * self.ratio_width, 
    #                         #     position.toPoint().y() * self.ratio_height
    #                         # )
    #                         print(f'Ctrl + Click: {self.p1}')

    #                     if mouse_event.modifiers() == (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier):
    #                         self.p2 = position.toPoint() * self.ratio_height
    #                         # self.p1 = QPoint(
    #                         #     position.toPoint().x() * self.ratio_width, 
    #                         #     position.toPoint().y() * self.ratio_height
    #                         # )
    #                         print(f'Ctrl + Shift + Click: {self.p2}')