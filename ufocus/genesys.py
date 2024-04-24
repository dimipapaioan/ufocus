# -*- coding: utf-8 -*-

from collections import deque
import logging
import time

from serial import Serial

logger = logging.getLogger(__name__)


class Genesys:
    """ 
    Class to programmatically control TDK-Lambda Genesys Power Supplies via their serial ports.
    """
    listening_address = deque([], maxlen=1)

    def __init__(self, address: int, serial_port: Serial) -> None:
        self.address = address
        self.serial_port = serial_port
        self.tries = 0

    # def __str__(self):
    #     return f'{self.get_identity()}\n{self.get_serial_number()}'

    def write_command(self, command: str) -> int:
        command += '\r'
        if (self.address not in self.listening_address):
            self.address_device(self.address)
            self.listening_address.append(self.address)
        return self.serial_port.write(command.encode('utf-8'))

    def read_response(self) -> str:
        return self.serial_port.read_until(b'\r').decode('utf-8').strip()

    def address_device(self, adr_num):
        adr = f"ADR {adr_num}\r"
        self.serial_port.write(adr.encode('utf-8'))
        time.sleep(0.1)
        try:
            assert (response := self.read_response()) == 'OK'
        except AssertionError:
            self.tries += 1
            if self.tries <= 3:
                logger.warning("PS did not respond, retrying last command")
                return self.repeat_last_command()
            else:
                self.tries = 0
                self.listening_address.append(adr_num)
                logger.error("Failed to send command")
                raise
        else:
            self.tries = 0
            return response
    
    def repeat_last_command(self) -> str:
        self.write_command("\\")
        return self.read_response()

    def get_identity(self):
        self.write_command("IDN?")
        return self.read_response()

    def get_serial_number(self):
        self.write_command("SN?")
        return self.read_response()

    def get_remote_mode(self):
        self.write_command("RMT?")
        return self.read_response()
    
    def get_power_status(self):
        self.write_command("OUT?")
        return self.read_response()

    def set_power_status(self, power):
        if power not in ("ON", "OFF"):
            raise ValueError("Invalid output, must be 'ON' or 'OFF'.")
        out = f"OUT {power}"
        self.write_command(out)
        return self.read_response()

    def set_remote_mode(self, mode):
        if mode not in ("LOC", "REM", "LLO"):
            raise ValueError(
                "Invalid Remote Mode, must be 'LOC', 'REM' or 'LLO'."
            )
        rmt = f"RMT {mode}"
        self.write_command(rmt)
        return self.read_response()

    def get_operation_mode(self):
        self.write_command("MODE?")
        return self.read_response()

    def set_programmed_voltage(self, volts):
        self.write_command(f"PV {volts}")  # :.3f?
        return self.read_response()

    def get_programmed_voltage(self):
        self.write_command("PV?")
        return self.read_response()

    def get_measured_voltage(self):
        self.write_command("MV?")
        return self.read_response()

    def set_programmed_current(self, amperes):
        self.write_command(f"PC {amperes}")  # :.3f?
        return self.read_response()

    def get_programmed_current(self):
        self.write_command("PC?")
        return self.read_response()

    def get_measured_current(self):
        self.write_command("MC?")
        return self.read_response()
    
    def get_status(self):
        self.write_command("STT?")
        return self.read_response()

    def get_voltage_and_current_data(self):
        self.write_command("DVC?")
        return self.read_response()
    
    def get_setting(self):
        self.write_command("MS?")
        return self.read_response()