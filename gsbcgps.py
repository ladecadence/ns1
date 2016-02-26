import datetime
import sys
import serial
import time

SERIAL_PORT = "/dev/ttyUSB0"
SERIAL_SPEED = "9600"

class GsbcGPS:
    def __init__(self, serial_port, serial_speed):
        self.latitude = 4331.50
	self.ns="N"
        self.longitude = 00536.76
	self.ew="W"
        self.altitude = 0
        self.sats = 0
        self.heading = 0
        self.speed = 0
        
        self.port = serial.Serial(serial_port, serial_speed, timeout=1)
    
    def update(self):
        # get GGA line from serial port
        self.line_gga = ""
        while self.line_gga[3:6] != "GGA":
            self.line_gga = self.port.readline()

        # and get RMC line from serial port
        self.line_rmc = ""
        while self.line_rmc[3:6] != "RMC":
            self.line_rmc = self.port.readline()

        # now parse data
        gga_data = self.line_gga.split(",")
        rmc_data = self.line_rmc.split(",")
        
        # good fix?
        if int(gga_data[7]) < 4:
            self.sats = int(gga_data[7])
            return
        
        # ok, good fix, record data
        self.latitude = gga_data[2]
        self.ns = gga_data[3]
        self.longitude = gga_data[4]
        self.ew = gga_data[5]
        self.sats = gga_data[7]
        self.altitude = gga_data[9]
        self.speed = rmc_data[7]
        self.heading = rmc_data[8]

    def good_fix(self):
        self.update()
        if self.sats >= 4:
            return True
        else:
            return False


if __name__ == "__main__":
    gps = GsbcGPS(SERIAL_PORT, SERIAL_SPEED)
    
    while 1:
        gps.update()
        #print gps.line_gga
        if gps.good_fix():
            print "sats: " + str(gps.sats),
            print ", lat: " + str(gps.latitude),
            print "" + str(gps.ns),
            print ", lon: " + str(gps.longitude),
            print "" + str(gps.ew),
            print ", alt: " + str(gps.altitude),
            print ", speed: " + str(gps.speed),
            print ", hdg: " + str(gps.heading)
        time.sleep(1)
