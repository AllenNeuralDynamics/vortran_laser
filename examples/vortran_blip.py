#!/usr/bin/env python3

from time import sleep
from vortran_laser.stradus import StradusLaser


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
