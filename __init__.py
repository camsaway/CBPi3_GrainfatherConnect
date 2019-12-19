# The purpose of this plug-in is to allow CBPi3 to communicate with a Grainfather Connect control box
# This would allow either control of a Grainfather by CBPi3 or use of a GrainfatherConnect control box with non-Grainfather hardware to provide wireless connection from CBPi3 to the brewery

# This code is based on/copied from https://github.com/john-0/gfx - Full credit to John-0

# NOTE: Requires pygatt to be installed: pip install pygatt (https://github.com/ampledata/pygatt)

# NOTE: I have personally experienced issues with GF BT connectivity when a device connects/disconnects. Sometimes even from the GF Community app I am unable to reconnect and have to reset the GF Controlbox to reconnect. In CBPi, this would also then mean restarting CBPi after restarting the control box.

from modules import cbpi
from modules.core.hardware import  SensorActive
from modules.core.props import Property
from modules.core.hardware import ActorBase

#GF Specific
import threading
import pygatt
from datetime import datetime, timedelta
import math
import time
CELSIUS = True
NAME = "Grain"
SERVICE = "0000cdd0-0000-1000-8000-00805f9b34fb"
WRITE = "0003cdd2-0000-1000-8000-00805f9b0131"
NOTIFY = "0003CDD1-0000-1000-8000-00805F9B0131"
STATUS_SCANNING = 0
STATUS_CONNECTING = 1
STATUS_DISCONNECTED = 2
STATUS_ERROR = 3
STATUS_CONNECTED = 100

def convertToUserUnits(value):
    if CELSIUS:
        return value
    return round((value * 9 / 5) + 32,1)

def convertToGrainfatherUnits(value):
    if CELSIUS:
        return value
    return round((value - 32) * 5 / 9)

class GFTimer():

    def __init__(self):
        self.h = 0
        self.m = 0
        self.s = 0
        self.initial = 0
        self.current = 0
        self.finished = False
        self.on = False
        self.notified = False

    def __getitem__(self, item):
        return getattr(self, item)

class GFXConnector():
  
    def __init__(self):
        self.current = 0
        self.target = 0
        self.pump = False
        self.heat = False
        self.delayedHeat = False
        self.lastBroadcast = 0
        self.timer = GFTimer()
        self.setStatus(STATUS_SCANNING, 'Scanning')        
        self.adapter = pygatt.backends.GATTToolBackend()
        self.adapter.start()
        
    def handle_data(self, handle, value):
        self.lastBroadcast = time.time()
        if len(value) != 17:
            return;
        try:
            value = value.replace('Z', '')
            values = value[1:].split(',')
            if chr(value[0]) == 'T':
                on = int(values[0]) > 0
                mins = int(values[1])
                s = int(values[3])
                if s < 60 and mins > 0:
                    mins = mins - 1
                if s == 60:
                    s = 0
                initial = int(values[2]) * 60
                if self.delayedHeat:
                    initial -= 60
                current = initial - (mins * 60) - s
                h = math.floor(mins / 60)
                m = mins % 60

                self.timer.h = h
                self.timer.m = m
                self.timer.s = s
                self.timer.current = current
                self.timer.initial = initial
                self.timer.finished = on and int(values[2]) == 0
                self.timer.on = on

                if self.timer.finished and not self.timer.notified:
                    self.timer.notified = True
              
                elif not self.timer.finished:
                    self.timer.notified = False

            elif chr(value[0]) == 'X':
                self.target = convertToUserUnits(float(values[0]))
                self.current = convertToUserUnits(float(values[1]))
                
            elif chr(value[0]) == 'Y':
                self.heat = int(values[0]) == 1
                self.pump = int(values[1]) == 1
                self.delayedHeat = int(values[7]) == 1

            # elif chr(value[0]) == 'W':                    
                

        except:
            e = sys.exc_info()[0]
            print "Failed to process input"
            print(e)

    def scan(self):
        self.setStatus(STATUS_SCANNING, 'Scanning')
        threading.Thread(target=self._scan).start()
    
    def __getitem__(self, item):
        return getattr(self, item)

    def _scan(self):
        try:
            devices = self.adapter.scan(run_as_root=True, timeout=3)
            for device in devices:
                if device['name'] == NAME:
                    self.setStatus(STATUS_CONNECTING, 'Connecting')
                    try:
                        self.device = self.adapter.connect(device['address'])
                        self.setStatus(STATUS_CONNECTED, 'Connected')
                        self.device.subscribe(NOTIFY, callback=self.handle_data)            
                        self.beep()
                        return
                    except pygatt.exceptions.NotConnectedError:
                        print("failed to connect to %s" % device)
                        self.setStatus(STATUS_ERROR, 'Failed to connect')
                        continue
            self.setStatus(STATUS_DISCONNECTED, 'No Grainfather found')
        except Exception, e:
            self.setStatus(STATUS_ERROR, 'Failed to scan devices: ' + str(e))

    def disconnect(self):
        self.lastBroadcast = 0
        if self.device:
            self.setStatus(STATUS_DISCONNECTED, 'Disconnected')
            self.device.disconnect()
            self.device = None

    def stop(self):
        self.adapter.stop()

    def setStatus(self, status, msg):
        self.status = status
        self.msg = msg

    def isHeating(self):
        return self.heat and self.current < self.target
  
    def setTemp(self, temp):
        temp = convertToGrainfatherUnits(temp)
        self._send("$%i," % temp)

    def beep(self):
        self._send("!")

    def togglePump(self):
        self._send("P")
    
    def pumpOn(self):
        if self.pump:
            self.togglePump()
        self.togglePump()
    
    def pumpOff(self):
        if self.pump:
            self.togglePump()
    
    def quitSession(self):
        self._send("Q1")

    def cancel(self):
        self._send("C0,")

    def cancelTimer(self):
        self._send("C")

    def pause(self):
        self._send("G")
    
    def setTimer(self, minutes):
        self._send("S%i" % minutes)

    def toggleHeat(self):
        self._send("H")
        
    def heatOn(self):
        if self.target != 100:
            self.setTemp(100)
        if self.heat == False:
            self.toggleHeat()
        
    def heatOff(self):
        if self.heat:
            self.toggleHeat()

    def tempUp(self):
        self._send("U")

    def tempDown(self):
        self._send("D")

    def setDelayedHeat(self, minutes):
        self._send("B%i,0," % minutes)

    def pressSet(self):
        self._send("T")

    def _send(self, cmd):
        if self.device:
            b = bytes(cmd.ljust(19))
            self.device.char_write(WRITE, bytearray(b), wait_for_response=False)
            self.sleep(0.5)
       
@cbpi.sensor
class Grainfather_TempSensor(SensorActive):

    temp = Property.Number("Temperature", configurable=False, default_value=5)

    def get_unit(self):
        '''
        :return: Unit of the sensor as string. Should not be longer than 3 characters
        '''
        return " C" if self.get_config_parameter("unit", "C") == "C" else " F"
        
    def stop(self):
        '''
        Stop the sensor. Is called when the sensor config is updated or the sensor is deleted
        :return: 
        '''
        try:
            gf
        except NameError:
            pass
        else:
            gf.disconnect()
            gf.stop()
            del gf
            
    def execute(self):
        '''
        Active sensor has to handle its own loop
        :return: 
        '''
        while self.is_running():
            self.temp = gf.current
            self.data_received(self.temp)
            self.sleep(2)

    @classmethod
    def init_global(cls):
        '''
        Called one at the startup for all sensors
        :return: 
        '''

        def initGF():
            try:
                gf
            except NameError:
                global gf
                gf = GFXConnector()
                gf.scan()
            else:
                pass
                
        initGF()

@cbpi.actor
class Grainfather_Pump(ActorBase):

    def on(self, power=0):
        '''
        Code to switch on the actor
        :param power: int value between 0 - 100
        :return: 
        '''
        
        gf.pumpOn()
        
    def off(self):
        '''
        Code to switch off the actor
        :return: 
        '''
        gf.pumpOff()

    def set_power(self, power):
        
        '''
        Optional: Set the power of your actor
        :param power: int value between 0 - 100
        :return: 
        '''
        pass

@cbpi.actor
class Grainfather_Heat(ActorBase):

    def on(self, power=0):
        '''
        Code to switch on the actor
        :param power: int value between 0 - 100
        :return: 
        '''
        gf.heatOn()
        
    def off(self):
        '''
        Code to switch off the actor
        :return: 
        '''
        gf.heatOff()

    def set_power(self, power):
        
        '''
        Optional: Set the power of your actor
        :param power: int value between 0 - 100
        :return: 
        '''
        pass

