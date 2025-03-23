# -*- coding: utf-8 -*-

import logging
from dataclasses import dataclass
from math import nan, inf, isnan

from PySide6.QtCore import (
    QObject,
    Signal,
    Slot,
    QRunnable,
)
from scipy.optimize import minimize, OptimizeResult

from image_processing import DetectedEllipse
from ps_controller import PSController
from settings_manager import SettingsManager


logger = logging.getLogger(__name__)


class MinimizerSignals(QObject):
    boundsError = Signal()
    updateCurrent = Signal(list)
    setCurrent = Signal(list)
    updateFunction = Signal(float)
    inAccumulation = Signal(bool)
    finished = Signal()


@dataclass
class PSCurrentsInfo:
    ps1_previous: float = nan
    ps2_previous: float = nan
    ps1_min: float = nan
    ps2_min: float = nan

    def update(self, c_new: list[float]) -> None:
        self.ps1_previous = float(c_new[0]) 
        self.ps2_previous = float(c_new[1])

    def update_min(self, min_new: list[float]) -> None:
        self.ps1_min = float(min_new[0])
        self.ps2_min = float(min_new[1])


@dataclass
class ObjectiveFunctionInfo:
    previous: float = nan
    delta: float = nan
    min_val: float = nan
    min_delta: float = nan


class Minimizer(QRunnable):
    def __init__(self, pscontroller: PSController, mutex, condition, parent=None) -> None:
        super().__init__(parent)
        self.parent = parent
        self.pscontroller = pscontroller
        self.control = False
        self.res = None
        self.mutex = mutex
        self.condition = condition
        self.solution = None
        self.settings_manager = SettingsManager()
        self.settings_manager.saveUserSettings()
        self.signals = MinimizerSignals()
        self.obj_func_stats = ObjectiveFunctionInfo()
        self.ps_currents_stats = PSCurrentsInfo()
        self.numerator_pow = 1
        self.denominator_pow = 2

        logger.info("Minimizer initialized")

    def run(self) -> None:
        logger.info("Minimizer started")
        self.pscontroller.signals.controlTimer.emit(True)
        self.signals.inAccumulation.emit(False)
        self.signals.setCurrent.connect(self.setPSCurrents)

        initial = [
            self.parent.spinboxInitialPS1.value(),
            self.parent.spinboxInitialPS2.value(),
        ]
        bounds = [
            (self.parent.spinboxMinPS1.value(), self.parent.spinboxMaxPS1.value()),
            (self.parent.spinboxMinPS2.value(), self.parent.spinboxMaxPS2.value()),
        ]
        try:
            self.numerator_pow, self.denominator_pow = eval(self.parent.lineEditObjFuncPowers.text())
        except (SyntaxError, ValueError) as err:
            logger.error(f"Obj. function powers have not been set correctly: {err}")
            logger.warning(f"Falling back to default values [{self.numerator_pow}, {self.denominator_pow}] "
                "for the numerator and the denominator, respectively"
            )

        try:
            self.solution: OptimizeResult = minimize(
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
            logger.error(f"Incorrect bounds: {bounds}")
            self.signals.boundsError.emit()
        else:
            logger.info(f"Solution: {self.solution.x}")
            self.signals.setCurrent.emit(self.solution.x)
        finally:
            self.pscontroller.refreshGUI()
            self.pscontroller.updateDialValue(self.pscontroller.ps1, self.parent.psLCD1)
            self.pscontroller.updateDialValue(self.pscontroller.ps2, self.parent.psLCD2)
            logger.info("Minimization process finished")
            self.pscontroller.signals.controlTimer.emit(False)
            self.signals.finished.emit()

    def callback(self, intermediate_result: OptimizeResult) -> None:
        logger.info(
            f"=== ITERATION ENDED ===\n"
            f"Best solution so far:\n"
            f"Q1 = {intermediate_result.x[0]:.4f} A\n"
            f"Q2/3 = {intermediate_result.x[1]:.4f} A\n"
            f"Obj. Func. = {intermediate_result.fun:.4f}\n"
        )
        if self.control:
            raise StopIteration

    def function(self, x) -> float:
        # Update current statistics
        self.ps_currents_stats.update(x)

        if not self.control:
            logger.info(
                f"Obj. Func. called with parameters: {x[0]:.4f} A, {x[1]:.4f} A"
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
                ellipse = self.set_res()
            finally:
                self.mutex.unlock()
                logger.debug("Lock released from minimizer")
                self.signals.inAccumulation.emit(False)

            # The function evaluation happens at this step and this is what the minimizer
            # uses to decide the next step. At this point maybe the value could be sent
            # to someplace else inside the code. The same functionality could be achieved
            # with the callback function.
            res = ellipse.area**self.numerator_pow / ellipse.circularity**self.denominator_pow

            self.signals.updateFunction.emit(res)

            self.update_statistics(x, res)

            self.pscontroller.refreshGUI()

            logger.info(f"Obj. Func. return value: {res:.2f}")
            logger.info(f"Objective funcion statistics: {self.obj_func_stats}")
            logger.info(f"PS currents statistics: {self.ps_currents_stats}")
        else:
            raise StopIteration
        return res

    @Slot(DetectedEllipse)
    def get_res(self, ellipse_data: DetectedEllipse) -> None:
        logger.debug("Got values from image processing")
        self.res = ellipse_data
        self.condition.wakeAll()

    def set_res(self) -> DetectedEllipse:
        logger.debug("Set values to minimizer")
        return self.res

    @Slot(list)
    def setPSCurrents(self, x: list[float]) -> None:
        logger.info(f"Setting Q1 current to: {x[0]}")
        self.pscontroller.setPS1Current(x[0] * 100)
        logger.info(f"Setting Q2/3 currents to: {x[1]}")
        self.pscontroller.setPS2Current(x[1] * 100)
    
    def update_statistics(self, currents: list[float], obj_ret: float) -> None:
        if not isnan(self.obj_func_stats.min_val):
            if self.obj_func_stats.min_val > obj_ret:
                self.obj_func_stats.min_val = obj_ret
                self.ps_currents_stats.update_min(currents)
                
            delta = obj_ret - self.obj_func_stats.previous
            if delta < self.obj_func_stats.min_delta:
                self.obj_func_stats.min_delta = delta
                
            self.obj_func_stats.delta = obj_ret - self.obj_func_stats.previous
            self.obj_func_stats.previous = obj_ret
                
        else:
            self.obj_func_stats.min_val = obj_ret
            self.obj_func_stats.previous = obj_ret
            self.obj_func_stats.min_delta = inf
            self.ps_currents_stats.update_min(currents)
