"""Stradus Laser Driver."""

import logging
from functools import cache
from time import perf_counter
from vortran_laser.device_codes import *
from serial import Serial, EIGHTBITS, STOPBITS_ONE, PARITY_NONE, \
    SerialTimeoutException


STRADUS_COM_SETUP = \
    {
        "baudrate": 19200,
        "bytesize": EIGHTBITS,
        "parity": PARITY_NONE,
        "stopbits": STOPBITS_ONE,
        "xonxoff": False,
        "timeout": 5
    }


class StradusLaser:

    REPLY_TERMINATION = b'\r\n'

    def __init__(self, port: str = "/dev/ttyUSB0"):
        # Create a logger for this port instance.
        self.log = logging.getLogger(f"{__name__}.{self.__class__.__name__}.{port}")
        self.ser = Serial(port, **STRADUS_COM_SETUP)
        self.ser.reset_input_buffer()
        # Since we're likely connected over an RS232-to-usb-serial interface,
        # ask for some sort of reply to make sure we're not timing out.
        try:
            # Put the interface into a known state to simplify communication.
            self._disable_echo()
            self._disable_prompt()
        except SerialTimeoutException:
            print(f"Connected to '{port}' but the device is not responding.")
            raise

    # Convenience functions
    def enable(self):
        """Enable emission."""
        self.set(Cmd.LaserEmission, BoolVal.ON)

    def disable(self):
        """disable emission."""
        self.set(Cmd.LaserEmission, BoolVal.OFF)

    @property
    @cache
    def wavelength(self):
        """return the current wavelength."""
        return int(self.get(Query.LaserWavelength))

    @property
    def temperature(self):
        """Return the current temperature as measured from the base plate."""
        return self.get(Query.BasePlateTemperature)

    @property
    def state(self) -> StradusState:
        """Return the laser state as a StradusState Enum.

        Note: The "FAULT" state encompasses many cases. A list of
            all specific fault codes can be accessed with get_faults().
        """
        fault_code = int(self.get(Query.FaultCode))
        # All Fault Codes >=4 represent some sort of issue.
        # Fault Codes <4 relate to laser state.
        if fault_code > StradusState.FAULT.value:
            return StradusState.FAULT
        return StradusState(fault_code)

    @property
    def interlock_is_closed(self):
        """True if the key is turned and laser is armed; False otherwise."""
        return True if BoolVal(self.get(Query.InterlockStatus)) else False

    @property
    def laser_is_emitting(self):
        """True if the laser is emitting. False otherwise."""
        return True if BoolVal(self.get(Query.LaserEmission)) else False

    def disable_cdrh(self):
        """disable 5-second delay"""
        self.set(Cmd.FiveSecEmissionDelay, BoolVal.OFF)

    def set_external_power_control(self):
        """Configure the laser to be controlled by an external analog input.

        0 to max output power is linearlly mapped to an analog voltage of 0-5V
        where any present power is ignored (datasheet, pg67).
        """
        self.set(Cmd.ExternalPowerControl, BoolVal.ON)

    def get_faults(self):
        """return a list of faults or empty list if no faults are present."""
        faults = []
        try:
            fault_code = int(self.get(Query.FaultCode))
        except ValueError:
            return None
        # Skip first Enum (LASER_EMISSION_ACTIVE), which is not really a fault.
        fault_code_fields = iter(FaultCodeField)
        next(fault_code_fields)
        for index, field in enumerate(fault_code_fields):
            if bin(fault_code)[-1] == '1':
                faults.append(field)
            fault_code = fault_code >> 1
            return faults

    # Utility functions to put the device in a known state.
    def _disable_echo(self):
        """Disable echo so that outgoing chars don't get echoed back."""
        self.set(Cmd.Echo, BoolVal.OFF)

    def _disable_prompt(self):
        """Disable prompt so that replies don't return with a prompt prefix."""
        self.set(Cmd.Prompt, BoolVal.OFF)

    # Low level Interface. All commands and queries can be accessed
    # through the get/set interface.
    def get(self, setting: Query) -> str:
        """Request a setting from the device."""
        reply = self._send(setting.value)
        return reply.lstrip(f"?{setting}= ")

    def set(self, cmd: Cmd, value: str) -> str:
        return self._send(f"{cmd}={value}")

    def _send(self, msg: str, raise_timeout: bool = True) -> str:
        """send a message and return the reply.

        :param msg: the message to send in string format
        :param raise_timeout: bool to indicate if we should raise an exception
            if we timed out.

        :returns: the reply (without line formatting chars) in str format
            or emptystring if no reply. Raises a timeout exception if flagged
            to do so.
        """
        # Note: Timing out on a serial port read does not throw an exception,
        #   so we need to do this manually.

        # All outgoing commands are bookended with a '\r\n' at the beginning
        # and end of the message.
        msg = f"{msg}\r"
        self.log.debug(f"Sending: {repr(msg.encode('ascii'))}")
        self.ser.write(f"{msg}".encode('ascii'))
        start_time = perf_counter()
        # Read the first '\r\n'.
        reply = self.ser.read_until(StradusLaser.REPLY_TERMINATION)
        self.log.debug(f"Received: {repr(reply)}")
        # Raise a timeout if we got no reply and have been flagged to do so.
        if not len(reply) and raise_timeout and \
                perf_counter()-start_time > self.ser.timeout:
            raise SerialTimeoutException
        start_time = perf_counter()  # Reset timeout counter.
        # Read the message and the last '\r\n'.
        reply = self.ser.read_until(StradusLaser.REPLY_TERMINATION)
        self.log.debug(f"Received: {repr(reply)}")
        if not len(reply) and raise_timeout and \
                perf_counter()-start_time > self.ser.timeout:
            raise SerialTimeoutException
        return reply.rstrip(StradusLaser.REPLY_TERMINATION).decode('utf-8')
