from stradus import StradusLaser
import logging
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

port = "COM3"
#ser = Serial(port, **STRADUS_COM_SETUP)

laser = StradusLaser(port)
print(laser.max_power)