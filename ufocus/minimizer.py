# -*- coding: utf-8 -*-

import logging
from math import pi, sqrt, nan

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
    QRunnable,
)
from scipy.optimize import minimize, OptimizeResult

from image_processing import DetectedEllipse


logger = logging.getLogger(__name__)


class MinimizerSignals(QObject):
    boundsError = Signal()
    updateCurrent = Signal(list)
    setCurrent = Signal(list)
    updateFunction = Signal(float)
    inAccumulation = Signal(bool)
    finished = Signal()


class Minimizer(QRunnable):

    def __init__(self, pscontroller, mutex, condition, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.pscontroller = pscontroller
        self.control = False
        self.res = None
        self.mutex = mutex
        self.condition = condition
        self.solution = None
        self.parent.settings_manager.saveUserSettings()
        self.signals = MinimizerSignals()

        logger.info("Minimizer initialized")

    def run(self):
        logger.info("Minimizer started")
        self.pscontroller.signals.controlTimer.emit(True)
        self.signals.inAccumulation.emit(False)

        initial = [
            self.parent.spinboxInitialPS1.value(),
            self.parent.spinboxInitialPS2.value(),
        ]
        bounds = [
            (self.parent.spinboxMinPS1.value(), self.parent.spinboxMaxPS1.value()),
            (self.parent.spinboxMinPS2.value(), self.parent.spinboxMaxPS2.value()),
        ]

        try:
            self.solution = minimize(
                fun=self.function,
                x0=initial,
                method="Nelder-Mead",
                bounds=bounds,
                callback=self.callback,
                options={
                    "return_all": True,
                    "xatol": float(self.parent.spinboxXATol.text()),
                    "fatol": float(self.parent.spinboxFATol.text()),
                    "maxiter": self.parent.spinboxMaxIter.value() if self.parent.spinboxMaxIter.value() != 0 else None,
                    "maxfev": self.parent.spinboxMaxFEval.value() if self.parent.spinboxMaxFEval.value() != 0 else None,
                    "disp": True,
                },
            )
        except StopIteration:
            logger.warning("Early stopping")
            self.solution = OptimizeResult(
                fun=nan, nit=0, nfev=0, status=99, x=[nan, nan]
            )
        except ValueError:
            logger.error("Incorrect bounds")
            self.signals.boundsError.emit()
        else:
            logger.info(f"Solution: {self.solution.x}")
            self.signals.setCurrent.emit(self.solution.x)
            # print(self.solution.allvecs)
        finally:
            self.pscontroller.refreshGUI()
            self.pscontroller.updateDialValue(self.pscontroller.ps1, self.parent.psLCD1)
            self.pscontroller.updateDialValue(self.pscontroller.ps2, self.parent.psLCD2)
            logger.info("Minimization process finished")
            self.pscontroller.signals.controlTimer.emit(False)
            self.signals.finished.emit()

    def callback(self, intermediate_result):
        logger.info(
            f"=== ITERATION ENDED ===\n"
            f"Best solution so far:\n"
            f"Q1 = {intermediate_result.x[0]:.4f} A\n"
            f"Q2/3 = {intermediate_result.x[1]:.4f} A\n"
            f"Min. Func. = {intermediate_result.fun:.4f}\n"
        )
        if self.control:
            raise StopIteration

    def function(self, x):
        if not self.control:
            logger.info(
                f"Min. Func. called with parameters: {x[0]:.4f} A, {x[1]:.4f} A"
            )
            # These values are to be sent to the power supplies
            self.signals.updateCurrent.emit(x)

            # self.pscontroller.setPS1Current(x[0] * 100)
            # self.pscontroller.setPS2Current(x[1] * 100)
            self.signals.setCurrent.emit(x)

            # Wait a bit for the system to adjust to the new currents or to gather data.
            # time.sleep(0.1)
            # Retrieve the values of what is to be minimized
            self.mutex.lock()
            try:
                logger.debug("Lock acquired from minimizer")
                self.signals.inAccumulation.emit(True)
                self.condition.wait(self.mutex)
                a, b = self.set_res()
            finally:
                self.mutex.unlock()
                logger.debug("Lock released from minimizer")
                self.signals.inAccumulation.emit(False)

            # The function evaluation happens at this step and this is what the minimizer
            # uses to decide the next step. At this point maybe the value could be sent
            # to someplace else inside the code. The same functionality could be achieved
            # with the callback function.
            res = (a * b) ** 2 * (
                1 / (4 * pi**2 * a * b / self.calculate_perimeter(a, b) ** 2) ** 3
            ) - 1.0
            self.signals.updateFunction.emit(res)
            self.pscontroller.refreshGUI()
            logger.info(f"Min. Func. return value: {res:.2f}")
        else:
            raise StopIteration
        return res

    @Slot(list)
    def get_res(self, ellipse_data: DetectedEllipse):
        logger.debug("Got values from image processing")
        self.res = (ellipse_data.major, ellipse_data.minor)
        self.condition.wakeAll()

    def set_res(self):
        logger.debug("Set values to minimizer")
        return self.res

    def calculate_perimeter(self, a, b):
        return pi * (3 * (a + b) - sqrt((3 * a + b) * (a + 3 * b)))
