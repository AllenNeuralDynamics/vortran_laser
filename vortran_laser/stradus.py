"""Stradus Laser Driver."""
import sys
import logging
from functools import cache
from time import perf_counter
from serial import Serial, EIGHTBITS, STOPBITS_ONE, PARITY_NONE, \
    SerialTimeoutException
from enum import Enum, IntEnum
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
    RecallFaultCode = "RFC"  # Recall Stored Fault codes
    FiveSecEmissionDelay = "DELAY"  # Enable/Disable 5-second CDRH delay
    ExternalPowerControl = "EPC"  # Enable(1)/Disable(0) External power control
    LaserEmission = "LE"  # Enable/Disable Laser Emission.
    LaserPower = "LP"  # Set laser power ###.# [mW]
    LaserCurrent = "LC"  # Set laser current ###.# [mA]
    PulsePower = "PP"  # Set Peak Pulse Power [0-1000] [mW]
    PulseMode = "PUL"  # Enable(1)/Disable(0) Pulse Mode (Digital Modulation)
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
    LaserOperatingHours = "?LH"  # Request laser operating hours.
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
class StradusState(IntEnum):
    LASER_EMISSION_ACTIVE = 0,
    STANDBY = 1,
    WARMUP = 2,
    FAULT = 3  # True if FaultCode > 32


# Boolean command value that can also be compared like a boolean.
class BoolVal(StrEnum):
    OFF = "0"
    ON = "1"

    def __bool__(self):
        return self.value == "1"

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

    @property
    def cdrh(self):
        status = self.get(Query.FiveSecEmissionDelay)
        return BoolVal(status)

    @cdrh.setter
    def cdrh(self, status: BoolVal or str):
        status = status if type(status) == BoolVal else BoolVal[status]
        self.set(Cmd.FiveSecEmissionDelay, status)
    @property
    def external_control(self):
        """Configure the laser to be controlled by an external analog input.

                0 to max output power is linearly mapped to an analog voltage of 0-5V
                where any present power is ignored (datasheet, pg67).
                """
        return self.get(Query.ExternalPowerControl)

    @external_control.setter
    def external_control(self, state: BoolVal or str):
        """Configure the laser to be controlled by an external analog input.

        0 to max output power is linearly mapped to an analog voltage of 0-5V
        where any present power is ignored (datasheet, pg67).
        """

        state = state if type(state) == BoolVal else BoolVal[state]
        self.set(Cmd.ExternalPowerControl, state)

    @property
    def max_power(self):
        """Returns maximum power of laser"""
        return self.get(Query.MaximumLaserPower)

    @property
    def faults(self):
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

    @property
    def power(self):
        """Returns current power of laser in mW"""
        return self.get(Query.LaserPower)

    @property
    def power_setpoint(self):
        """Returns current power of laser in mW"""

        if self.get(Query.PulseMode) == '1':
            return self.get(Query.PulsePower)

        else:
            return self.get(Query.LaserPowerSetting)

    @power_setpoint.setter
    def power_setpoint(self, value: float):
        """Set laser power setpoint. If in digital modulation mode set pulse power else set power"""
        if self.get(Query.PulseMode) == '1':
            self.set(Cmd.PulsePower, value)
        else:
            self.set(Cmd.LaserPower, value)
        self.set(Cmd.LaserPower, value)

    @property
    def digital_modulation(self):
        """Return if digital modulation mode is on or off"""
        return BoolVal(self.get(Query.PulseMode))

    @digital_modulation.setter
    def digital_modulation(self, value: BoolVal or str):
        """Set digital modulation mode.
        Note if laser in constant power mode, digital modulation can't be turned on"""
        value = value if type(value) == BoolVal else BoolVal[value]
        if self.constant_current == BoolVal.OFF:
            self.log.warning(
                f'Laser is in constant power mode and cannot be put in digital modulation mode')
        else:
            self.set(Cmd.PulseMode, value)

    @property
    def constant_current(self):
        """Return if constant current is on or off.
        Note digital modulation can only be on in constant current mode"""
        return BoolVal(self.get(Query.LaserDriverControlMode))

    @constant_current.setter
    def constant_current(self, value: BoolVal or str):
        """Set constant current mode on or off"""
        value = value if type(value) == BoolVal else BoolVal[value]
        if value == BoolVal.OFF and self.digital_modulation == BoolVal.ON:
            self.log.warning(
                f'Putting Laser in constant power mode and disabling digital modulation mode')
        self.set(Cmd.LaserDriverControlMode, value)

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
        #print(f"Sending: {repr(msg.encode('ascii'))}")
        self.ser.write(f"{msg}".encode('ascii'))
        start_time = perf_counter()
        # Read the first '\r\n'.
        reply = self.ser.read_until(StradusLaser.REPLY_TERMINATION)
        # Raise a timeout if we got no reply and have been flagged to do so.
        if not len(reply) and raise_timeout and \
                perf_counter()-start_time > self.ser.timeout:
            raise SerialTimeoutException
        start_time = perf_counter()  # Reset timeout counter.
        # Read the message and the last '\r\n'.
        reply = self.ser.read_until(StradusLaser.REPLY_TERMINATION)
        self.log.debug(f"Received: {repr(reply)}")
        #print(f"Received: {repr(reply)}")
        if not len(reply) and raise_timeout and \
                perf_counter()-start_time > self.ser.timeout:
            raise SerialTimeoutException
        return reply.rstrip(StradusLaser.REPLY_TERMINATION).decode('utf-8')
