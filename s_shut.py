#!/usr/bin/env python3

# MIT License
# copyright (c) 2021 Klaus Mezger, ECOM Engineering
import argparse

''' Simple python 3.x shutdown control using switch and LED

This script allows a controlled shutdown.
Switch:
    press >5 seconds:  secure system shutdown is triggered
    double click:      secure shutdown and restart
LED:
    turns on, as soon as raspberry is ready
    turns off, as soon as controlled power down is compleded

For help use commandline "python s_shut.py -h"
For auto start call script from file /etc/rc.local:
    /home/pi/Projects/Utils/Shutdown/Debug/./s_shut.py

Hardware component used:
    * 330Ohm resistor
    * Low current (green) LED
    * SPST switch 
Connections:
    * Raspi output port --> LED(anode)-LED(cathode) --> resistor --> GND
    * Raspi input Port --> switch --> GND
    * [optional, if not programmed in config.txt) Raspi input Port --> 10kOhm resistor to 3.3V]
Prerequisites, if no external pullup for switch:
    * Enable internal pullup on input port on bottom in file /boot/config.txt
        #set GPIO20 as input with pullup high
        gpio=20=ip,pu 
    
'''


def getArgs():
    '''Read arguments from command line'''

    ledDefault = 21
    switchDefault = 20
    powerDefault = ''
 
 
    parser = argparse.ArgumentParser()
                                        
    parser.add_argument("-l","--ledPort", type=int, default=ledDefault, metavar='',
                        help='LED output bcm port default = ' + str(ledDefault))
    parser.add_argument("-s", "--switchPort", type=int, default=switchDefault, metavar='',
                        help='Switch control input bcm port default = ' + str(switchDefault))
    parser.add_argument("-p", "--powerPort", type=int, metavar='',
                        help='Optional bcm port for external power timer')

    args=parser.parse_args()
    portHandler(args)

def portHandler(ports):

    print('LED: GPIO'+str(ports.ledPort),
          'Switch: GPIO'+str(ports.switchPort),
          'Power: GPIO'+str(ports.powerPort))

    chip = gpiod.Chip("0")
    inPort = chip.get_line(ports.switchPort)
    inPort.request("UPS-2", type=gpiod.LINE_REQ_EV_BOTH_EDGES)

    outPort = chip.get_line(ports.ledPort)
    outPort.request("Py_Shutdown", type=gpiod.LINE_REQ_DIR_OUT)
    outPort.set_value(1) #signal raspi is up

    counter = 0
    t_keyrelease = time.time()
    while True:
        try:
            keyAction = "NO_KEY"
            #wait for key pressed
            event = inPort.event_read() #falling edge: key pressed
            print(event)
            print("type", event.type)
            print('timestamp: {}.{}'.format(event.sec, event.nsec))
            if (event.type == 1):
                print("first event should be falling --> ignore")
                continue #retry wait for falling edge
            counter = 1
            t_keypress = event.sec + (event.nsec * 10e-10)
            pauseTime = t_keypress - t_keyrelease 
            
            #wait for key released
            event = inPort.event_read() #rising edge: key released
            print("type", event.type)
            print('timestamp: {}.{}'.format(event.sec, event.nsec))
            t_keyrelease = event.sec + (event.nsec * 10e-10)
            pulseTime = t_keyrelease - t_keypress

            counter = counter + 1
            print("counter =", counter,
            "  pulse time= ", pulseTime, "s"
            "  pause time = ", pauseTime)

            #analyze command
            if pulseTime < 0.5:
                if pauseTime < 0.5: #this is a double click
                    keyAction = "DOUBLE_PRESS"
                    os.system("sudo shutdown -r now")
                else:
                    keyAction = "SHORT_PRESS"
            elif pulseTime > 5:
                keyAction = "SUPER_LONG_PRESS"
                #power down needs power off through external circuitry
                os.system("'sudo shutdown -P now")      
            elif pulseTime > 2:
                keyAction = "LONG_PRESS"
                os.system("sudo shutdown -h now")

            print("keyAction =", keyAction)             
                    
        except KeyboardInterrupt:
            chip.close()
            break
    print("ciao")

if __name__ == "__main__":
    import gpiod
    import time
    import sys
    import os
    getArgs()
