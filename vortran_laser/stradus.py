"""Stradus Laser Driver."""

import sys
from enum import Enum, IntEnum
from time import perf_counter

import serial
from serial import Serial, EIGHTBITS, STOPBITS_ONE, PARITY_NONE, \
    SerialTimeoutException

# Define StrEnums if they don't yet exist.
if sys.version_info < (3, 11):
    class StrEnum(str, Enum):
        pass
else:
    from enum import StrEnum


class Cmd(StrEnum):
    Echo = "ECHO"  # Enable(1)/Disable(0) echoing back every input character
    Prompt = "PROMPT"  # Enable(1)/Disable(0) a prompt
    LaserDriverControlMode = "C"  # Set laser mode: [Power=0, Current=1]
    ClearFaultCode = "CFC"  # Clear stored fault code
    RecallFaultCode =  "RFC"  # Recall Stored Fault codes
    FiveSecEmissionDelay = "DELAY"  # Enable/Disable 5-second CDRH delay
    ExternalPowerControl = "EPC"  # Enable(1)/Disable(0) External power control
    LaserEmission = "LE"  # Enable/Disable Laser Emission.
    LaserPower = "LP"  # Set laser power ###.# [mW]
    LaserCurrent = "LC"  # Set laser current ###.# [mA]
    PulsePower = "PP"  # Set Peak Pulse Power [0-1000] [mW]
    PulseMode = "PM"  # Enable(1)/Disable(0) Pulse Mode
    ThermalElectricCooler = "TEC"  # Toggle TEC [Off=0, On=1]


class Query(StrEnum):
    BasePlateTemperature = "?BPT"
    SystemFirmwareVersion = "?SFV"
    SystemFirmwareProtocolVersion = "?SPV"

    LaserDriverControlMode = "?C"  # request laser drive control status
    ComputerControl = "?CC"  # request computer control status
    FiveSecEmissionDelay = "?DELAY"  # Request 5-second CDRH Delay status
    EchoStatus = "?ECHO"  # Request Echo Status (echo turned off or on)
    ExternalPowerControl = "?EPC"  # Request external power control
    FaultCode = "?FC"  # Request fault code and clear faults
    FaultDescription = "?FD"  # Request fault description.
    FirmwareProtocol = "?FP"  # Request protocol version.
    FirmwareVersion = "?FV"  # Request Firmware version.
    Help = "?H"  # Request help file
    InterlockStatus = "?IL" # Request interlock status
    LaserCurrent = "?LC"  # Request measured laser current
    LaserCurrentSetting = "?LCS"  # Request desired laser current setpoint
    LaserEmission = "?LE"  # Request laser emission status.
    LaserOperatingHourse = "?LH"  # Request laser operating hours.
    LaserIdentification = "?LI"  # Request Laser identification.
    LaserPower = "?LP"  # Request measured laser power.
    LaserPowerSetting = "?LPS"  # Request desired laser power setpoint.
    LaserWavelength = "?LW"  # Request laser wavelength.
    MaximumLaserPower = "?MAXP"  # Request maximum laser power.
    OpticalBlockTemperature = "?OBT"  # Request optical block temperature (obt)
    OpticalBlockTemperatureSetting = "?OBTS"  # Request desired obt setpoint
    PulsePower = "?PP"  # Request peak laser power.
    RatedPower = "?RP"  # Request rated laser power.
    PulseMode = "?PUL"  # Request pulse mode.
    ThermalElectricCoolerStatus = "?TEC" # Request TEC status.


# Requesting a FaultCode will return a 16-bit number who's bitfields
# represent which faults are active.
# Many fields (bits) can be asserted at once.
class FaultCodeField(IntEnum):
    LASER_EMISSION_ACTIVE = 0
    STANDBY = 1
    WARMUP = 2
    VALUE_OUT_OF_RANGE = 4
    INVALID_COMMAND = 8
    INTERLOCK_OPEN = 16
    TEC_OFF = 32
    DIODE_OVER_CURRENT = 64
    DIODE_TEMPERATURE_FAULT = 128
    BASE_PLATE_TEMPERATURE_FAULT = 256
    POWER_LOCK_LOST = 512
    EEPROM_ERROR = 1024
    I2C_ERROR = 2048
    FAN = 4096
    POWER_SUPPLY = 8192
    TEMPERATURE = 16384
    DIODE_END_OF_LIFE_INDICATOR = 32768


# Laser State Representation
class LaserState(IntEnum):
    LASER_EMISSION_ACTIVE = 0,
    STANDBY = 1,
    WARMUP = 2,
    FAULT = 3  # True if FaultCode > 32


# Boolean command value.
class BoolVal(StrEnum):
    OFF = "0"
    ON = "1"


STRADUS_COM_SETUP = \
    {
        "baudrate": 19200,
        "bytesize": EIGHTBITS,
        "parity": PARITY_NONE,
        "stopbits": STOPBITS_ONE,
        "xonxoff": False,
        "timeout": 1
    }


class StradusLaser:

    REPLY_TERMINATION = b'\r\n'

    def __init__(self, port: str = "/dev/ttyUSB0"):
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

    def disable_cdrh(self):
        """disable 5-second delay"""
        self.set(Cmd.FiveSecEmissionDelay, BoolVal.OFF)

    def set_external_power_control(self):
        """Configure the laser to be controlled by an external analog input.

        0 to max output power is linearlly mapped to an analog voltage of 0-5V
        where any present power is ignored (datasheet, pg67).
        """
        self.set(Cmd.ExternalPowerControl, BoolVal.ON)

    def get_state(self) -> LaserState:
        fault_code = int(self.get(Query.FaultCode))
        if fault_code > LaserState.FAULT.value:
            return LaserState.FAULT
        return LaserState(fault_code)

    def get_faults(self):
        """return a list of faults or empty list if no faults are present."""
        faults = []
        try:
            fault_code = int(self.get(Query.FaultCode))
        except ValueError:
            return None
        for index, field in enumerate(FaultCodeField):
            if bin(fault_code)[-1] == '1':
                faults.append(field)
            fault_code = fault_code >> 1
            return faults

    # Low level Interface. All commands and queries can be accessed
    # through the get/set interface.
    def _disable_echo(self):
        """Disable echo so that outgoing chars don't get echoed back."""
        self.set(Cmd.Echo, BoolVal.OFF)

    def _disable_prompt(self):
        """Disable prompt so that replies don't return with a prompt prefix."""
        self.set(Cmd.Prompt, BoolVal.OFF)

    def get(self, setting: Query) -> str:
        """Request a setting from the device."""
        reply = self._send(setting.value)
        return reply.lstrip(f"?{setting}=")

    def set(self, cmd: Cmd, value: str) -> str:
        # TODO: is this always empty string?
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
        # Note: timing out from a serial port read does not throw an exception,
        #   so we need to do this manually.

        # all outgoing commands are bookended with a '\r\n' at the beginning
        # and end of the message.
        self.ser.write(f"{msg}\r".encode('ascii'))
        start_time = perf_counter()
        # Read the first '\r\n'.
        reply = self.ser.read_until(StradusLaser.REPLY_TERMINATION)
        # Raise a timeout if we got no reply and have been flagged to do so.
        if not len(reply) and raise_timeout and \
                perf_counter()-start_time > self.ser.timeout:
            raise SerialTimeoutException
        start_time = perf_counter()  # Reset this.
        # Read the message and the last '\r\n'.
        reply = self.ser.read_until(StradusLaser.REPLY_TERMINATION)
        if not len(reply) and raise_timeout and \
                perf_counter()-start_time > self.ser.timeout:
            raise SerialTimeoutException
        return reply.rstrip(StradusLaser.REPLY_TERMINATION).decode('utf-8')

