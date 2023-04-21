#!/usr/bin/env python3

from time import sleep
from vortran_laser.stradus import StradusLaser, StradusState


PORT = "/dev/ttyUSB0"

laser = StradusLaser(PORT)

if not laser.interlock_is_closed:
    print(f"Note: {laser.wavelength}[nm] Laser is not armed via external key.")

if laser.state == StradusState.FAULT:
    print(f"Laser in a fault state. Error codes are: {laser.get_faults()}")

print("Enabling laser!")
laser.enable()
sleep(0.25)
print("Disabling laser!")
laser.disable()
print("Done!")

# Setup for Dispsim
# 1. Disable External Power Control
# 2. Enable Pulse Mode (digital modulation) (first time we do this, reply is empty or took too long?)
# 3. Disable CDRH
# 4. Enable Laser Emission