# CBPi3_GrainfatherConnect
Plug-In for CraftBeerPi3 to integrate with Grainfather Connect bluetooth control box (sensor and actors)

This plug-in will allow you to connect to a Grainfather Connect bluetooth control box. I see 2 uses for this;
1) To allow a grainfather to be operated from CBPi instead of the Grainfather app
2) To allow the use of a grainfather connect control box to provide wireless connectivity to a brewery. This takes away the need to for builds/wiring that many people are not skilled to do.

# The plug-in requires pygatt to be installed.
pip install pygatt (https://github.com/ampledata/pygatt)

Your RPi running CBPi3 must be located close-enough to the control box for a stable bluetooth connection.
You can only connect 1 device to a grainfather controller at a time (so make sure you don't have the GF app connected or this will fail).
Make sure the Grainfather controller is on and ready to pair before starting CBPi
If you lose connection you will need to restart the grainfatehr controller, and then CBPi (note: this is the same as with the GF app).


To Do List;
1) Find a way for the actors to push back status to CBPi (you can override by manually pressing the buttons and CBPi doesn't know)
2) Find a better way for managing the BT connection, and re-connects if the connection is lost
3) Potentially find an option to use the built-in grainfather PID logic
4) Look at some of the more complex GF features like boil temp, temperature units, etc.


Note: this is my first python project so any comments/help/suggestions would be greatly appreciated.



* This code is based on/largely copied from https://github.com/john-0/gfx - Full credit to John-0 for his work
