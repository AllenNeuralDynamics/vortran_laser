A minimal python driver for communicating with a Vortran Stradus Laser over an
RS232 interface.


## Python Driver Installation
From this directory, invoke:

````
pip install -e .
````

## Example Usage
````python
from time import sleep
from vortran_laser.stradus import StradusLaser, StradusState

laser = StradusLaser('COM10')

if not laser.interlock_is_closed:
    print(f"Note: {laser.wavelength}[nm] Laser is not armed via external key.")
    
if laser.state == StradusState.FAULT:
    print(f"Laser in a fault state. Error codes are: {laser.get_faults()}")

print("Enabling laser!")
laser.enable()
sleep(0.25)
print("Disabling laser!")
laser.disable()
````

If you need more granularity beyond the convenience functions, every device
query and command can be manipulated via the get/set interface.

````python
from vortran_laser.stradus import Cmd, Query

print(f"{laser.get(Query.FiveSecEmissionDelay)}")
print(f"{laser.get(Query.PulsePower)}")
print(f"{laser.get(Query.MaximumLaserPower)}")

laser.set(Cmd.PulsePower, round(10/3, 1))
laser.set(Cmd.PulsePower, round(10/3, 1))
````
The get/set interface returns strings throughout.


## FAQs

*Q: Does this driver work if you connect directly to the USB mini cable on the
back of the Stradus laser itself?"*

A: No, the USB connector exposes a native USB (HID) interface that does not
have its command set documented.
This interface is for the RS232 interface only.
