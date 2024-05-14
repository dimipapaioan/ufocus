# -*- coding: utf-8 -*-

import logging
from queue import Queue
from re import compile
from threading import Thread

from PySide6.QtCore import (
    QObject, Signal, Slot, QRunnable, QTimer, QEventLoop
)

from genesys import Genesys


logger = logging.getLogger(__name__)


class PSControllerSignals(QObject):
    updateValues = Signal(dict)
    serialConnectionSuccessful = Signal(bool)
    controlTimer = Signal(bool)
    terminate = Signal()

class PSController(QRunnable):

    def __init__(self, serial_port, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.serial_port = serial_port
        self.ps1 = None
        self.ps2 = None
        self.pattern = compile(r'(\d+\.*\d*)')
        self.data = {
            'MV1': None, 'PV1': None, 'MC1': None, 'PC1': None,
            'MV2': None, 'PV2': None, 'MC2': None, 'PC2': None,
        }
        self.successfull = {'PS1': False, 'PS2': False}
        self.queue = Queue()
        self.queue_thread = None
        self.control = True
        self.signals = PSControllerSignals(self.parent)


    def run(self):
        # Create the objects controlling the power supplies
        self.ps1 = Genesys(6, self.serial_port)
        self.ps2 = Genesys(7, self.serial_port)

        # Connect the power supplies
        try:
            self.ps1.set_power_status("ON")
        except AssertionError:
            logger.error("PS1: No response from device")
            self.successfull['PS1'] = False
        else:
            self.successfull['PS1'] = True
            logger.info(f"PS1: {self.ps1.get_power_status()}")
            self.updateDialValue(self.ps1, self.parent.psLCD1)
        
        try:
            self.ps2.set_power_status("ON")
        except AssertionError:
            logger.error("PS2: No response from device")
            self.successfull['PS2'] = False
        else:
            self.successfull['PS2'] = True
            logger.info(f"PS2: {self.ps2.get_power_status()}")
            self.updateDialValue(self.ps2, self.parent.psLCD2)

        if all(self.successfull.values()):
            # Signal that the connection has been successful
            self.signals.serialConnectionSuccessful.emit(True)

            # Add a timer to refresh the state of the power supplies
            self.refreshTimer = QTimer()
            self.refreshTimer.setInterval(1000)
            self.refreshTimer.timeout.connect(self.refreshGUI)
            self.signals.controlTimer.connect(self.controlTimer)

            # Start the thread that manages the queue and update the GUI
            self.queue_thread = Thread(target=self.commandWorker, daemon=True)
            self.queue_thread.start()
            self.refreshGUI()
            
            # Start the timer and the event loop
            logger.debug("Started refresh timer")
            self.refreshTimer.start()
            self.loop = QEventLoop()
            self.loop.exec()

            # If we reach this point, the loop has been terminated
            logger.debug("Event loop terminated")

            self.refreshTimer.stop()
            logger.debug("Stopped refresh timer")

            self.queue.put((self.ps1.set_power_status, 'OFF'))
            self.queue.join()
            logger.info(f"PS1: {self.response}")
            self.queue.put((self.ps2.set_power_status, 'OFF'))
            self.queue.join()
            logger.info(f"PS2: {self.response}")
            self.parent.psLCD1.setEnabled(False)
            self.parent.psLCD2.setEnabled(False)
        elif any(self.successfull.values()):
            logger.critical("Could not connect to one of the power supplies")
            self.signals.serialConnectionSuccessful.emit(False)
            if self.successfull['PS1']:
                self.ps1.set_power_status("OFF")
            if self.successfull['PS2']:
                self.ps2.set_power_status("OFF")
        else:
            logger.critical("Could not connect the power supplies")
            self.signals.serialConnectionSuccessful.emit(False)

        self.signals.terminate.emit()
    
    def commandWorker(self):
        while self.control or self.queue.empty():
            func, val = self.queue.get()
            logger.debug("Command sent. Waiting on response...")
            if val is None:
                self.response_st = func()
                logger.debug(f"Response: {self.response_st}")
            else:
                self.response = func(val)
                logger.debug(f"Response: {self.response}")
            self.queue.task_done()

    @Slot()
    def refreshGUI(self):
        # print("Timed out.")
        self.queue.put((self.ps1.get_status, None))
        self.queue.join()
        ps1_status = self.pattern.findall(self.response_st)

        self.queue.put((self.ps2.get_status, None))
        self.queue.join()
        ps2_status = self.pattern.findall(self.response_st)

        try:
            self.data.update(
                [('MV1', ps1_status[0]), ('PV1', ps1_status[1]),('MC1', ps1_status[2]), ('PC1', ps1_status[3]), 
                 ('MV2', ps2_status[0]), ('PV2', ps2_status[1]),('MC2', ps2_status[2]), ('PC2', ps2_status[3]),]
            )
        except IndexError:
            self.signals.updateValues.emit(
                {'MV1': '---', 'MC1': '---', 'MV2': '---', 'MC2': '---'}
            )
        else:
            self.signals.updateValues.emit(self.data)

    @Slot(int)
    def setPS1Current(self, value):
        self.queue.put((self.ps1.set_programmed_current, value / 100))
        # self.queue.join()
    
    @Slot(int)
    def setPS2Current(self, value):
        self.queue.put((self.ps2.set_programmed_current, value / 100))
        # self.queue.join()

    @Slot(bool)
    def controlTimer(self, b):
        if b:
            self.refreshTimer.stop()
        else:
            self.refreshTimer.start()

    def updateDialValue(self, ps, widget):
        if (val := float(ps.get_programmed_current())) != widget.currentDial.value() / 100:
                widget.currentDial.blockSignals(True)
                widget.currentDial.setValue(int(val * 100))
                widget.currentDial.blockSignals(False)
