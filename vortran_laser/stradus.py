"""Stradus Laser Driver."""

import sys
from enum import Enum, IntEnum
from serial import Serial, EIGHTBITS, STOPBITS_ONE, PARITY_NONE

# Define StrEnums if they don't yet exist.
if sys.version_info < (3,11):
    class StrEnum(str, Enum):
        pass


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
    "timeout": 0.25
}


class StradusLaser:

    REPLY_TERMINATION = b'\r\n'

    def __init__(self, port: str = "/dev/ttyUSB0"):
        self.ser = Serial(port, **STRADUS_COM_SETUP)
        self.ser.reset_input_buffer()
        # Put the interface into a known state to simplify communication.
        self._disable_echo()
        self._disable_prompt()

    def enable(self):
        """Enable emission."""
        self.set(Cmd.LaserEmission, BoolVal.ON)

    def disable(self):
        """disable emission."""
        self.set(Cmd.LaserEmission, BoolVal.OFF)

    def set_external_power_control(self):
        self.set(Cmd.ExternalPowerControl, BoolVal.ON)



    def get_faults(self):
        """return a list of fault codes."""
        fault_code = int(self.get(FaultCode))
        faults = []
        for index, fault_code_field in enumerate(FaultCodeField):
            fault_code = fault_code >> 1
            if bin(fault_code)[-1]:
                faults.append(fault_code_field)
        return faults

    def clear_faults(self):
        pass

    # Low level Interface.
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

    def _send(self, msg: str, no_reply: bool = False) -> str:
        """send a message and return the reply.

        :param noreply: true if this particular command does not issue a reply.

        :returns: the reply (without line formatting chars) in str format
            or emptystring if no reply.
        """
        # Laser commands are bookended with '\r\n' at the start and end
        # of a reply. If a command responds with no reply, then only a single
        # '\r\n' is returned.
        self.ser.write(f"{msg}\r".encode('ascii'))
        reply = self.ser.read_until(StradusLaser.REPLY_TERMINATION)
        if no_reply:
            return ""
        # If this command actually doesn't reply, then we will just timeour
        # and return emptystring.
        reply = self.ser.read_until(StradusLaser.REPLY_TERMINATION)
        return reply.rstrip(StradusLaser.REPLY_TERMINATION).decode('utf-8')


if __name__ == "__main__":

    from inpromptu import Inpromptu
    laserui = Inpromptu(StradusLaser('/dev/ttyUSB0'))
    laserui.cmdloop()
