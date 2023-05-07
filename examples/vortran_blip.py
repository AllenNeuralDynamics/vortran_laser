#!/usr/bin/env python3

from time import sleep
from vortran_laser.stradus import StradusLaser, StradusState, Cmd, BoolVal
import logging

# Print log messages to the screen so we can see every outgoing tiger message.
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.StreamHandler())
logger.handlers[-1].setFormatter(
   logging.Formatter(fmt='%(asctime)s:%(levelname)s: %(message)s'))


PORT = "COM12"#"/dev/ttyUSB0"

laser = StradusLaser(PORT)

if not laser.interlock_is_closed:
    print(f"Note: {laser.wavelength}[nm] Laser is not armed via external key.")

if laser.state == StradusState.FAULT:
    print(f"Laser in a fault state. Error codes are: {laser.get_faults()}")
#laser.set_external_power_control_state(False)  # Disable External Power Control
laser.set(Cmd.LaserDriverControlMode, 0)  # Constant Power Mode
laser.set(Cmd.PulseMode, 1)  # Digital Modulation. # FIXME: confirm this gets sent
# FIXME: above command can be rejected.
laser.set(Cmd.PulsePower, 25)
laser.disable_cdrh()  # Disable 5 second delay before start of emission per datasheet 11.2
print("Enabling laser!")
laser.enable()
sleep(0.25)
input("Press Enter to disable emission.")
print("Disabling laser!")
laser.disable()
print("Done!")

# Setup for Dispsim
# 1. Disable External Power Control
# 2. Enable Pulse Mode (digital modulation) (first time we do this, reply is empty or took too long?)
# 3. Disable CDRH
# 4. Enable Laser Emission