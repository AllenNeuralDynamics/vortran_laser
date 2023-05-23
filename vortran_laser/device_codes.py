"""Device Codes for Stradus Laser"""
import sys
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