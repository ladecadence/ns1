import datetime
import sys
import serial
import time
import os

SERIAL_PORT = "/dev/ttyAMA0"
SERIAL_SPEED = "9600"

class AshabGPS:
    def __init__(self, serial_port, serial_speed):
        self.time = "000000.00"
        self.latitude = "4332.94"
        self.ns="N"
        self.longitude = "00539.78"
        self.ew="W"
        self.altitude = 0
        self.sats = 0
        self.heading = 0
        self.speed = 0
        self.line_gga = ""
        self.line_rmc = ""

        self.port = serial.Serial(serial_port, serial_speed, timeout=3)

    def update(self):
        # discard old data
        self.port.flushInput()
        # get GGA line from serial port
        self.line_gga = ""
        count = 0
        while self.line_gga[3:6] != "GGA":
            self.line_gga = self.port.readline().decode('cp850')
            count = count + 1
            if count > 9:
                self.line_gga=""
                break

        # and get RMC line from serial port
        self.line_rmc = ""
        count = 0
        while self.line_rmc[3:6] != "RMC":
            self.line_rmc = self.port.readline().decode('cp850')
            count = count + 1
            if count > 9:
                self.line_rmc=""
                break


        # now parse data
        gga_data = self.line_gga.split(",")
        rmc_data = self.line_rmc.split(",")

        if len(gga_data) >= 9 and len(rmc_data) >=8:
            try:         
                self.time = gga_data[1]
                # good fix?
                if int(gga_data[7]) < 4:
                    self.sats = int(gga_data[7])
                    return

                # ok, good fix, record data
                self.latitude = gga_data[2]
                self.ns = gga_data[3]
                self.longitude = gga_data[4]
                self.ew = gga_data[5]
                self.sats = int(gga_data[7])
                self.altitude = gga_data[9]
                self.speed = rmc_data[7]
                self.heading = rmc_data[8]
                if self.heading == "":
                    self.heading = 0
            except:
                pass

    def good_fix(self):
        self.update()
        if self.sats >= 4:
            return True
        else:
            return False

    def decimal_longitude(self):
        try:
            degrees = float(self.longitude[:3])
            fraction = float(self.longitude[3:]) / 60
        except:
            degrees = 0
            fraction = 0

        return degrees + fraction

    def decimal_latitude(self):
        try:
            degrees = float(self.latitude[:2])
            fraction = float(self.latitude[2:]) / 60
        except:
            degrees = 0
            fraction = 0

        return degrees + fraction

    def get_time(self):
        return (self.time[:2], self.time[2:4], self.time[4:])

    def set_system_time(self):
        date_cmd = "sudo date --set=\"" + self.time[:2] + ":" + self.time[2:4] + \
                    ":" + self.time[4:] + "\""
        stat = os.system(date_cmd)
        return stat


if __name__ == "__main__":
   
    if len(sys.argv) < 2:
        gps = AshabGPS(SERIAL_PORT, SERIAL_SPEED)
    else:
        gps = AshabGPS(sys.argv[1], SERIAL_SPEED)

    while 1:
        gps.update()
        if gps.good_fix():
            print( "sats: " + str(gps.sats))
            print( ", lat: " + str(gps.latitude))
            print( "" + str(gps.ns))
            print( ", lon: " + str(gps.longitude))
            print( "" + str(gps.ew))
            print( ", alt: " + str(gps.altitude))
            print( ", speed: " + str(gps.speed))
            print( ", hdg: " + str(gps.heading))
            #print(gps.line_gga)
        else:
            print(gps.line_gga)
            print(gps.get_time())
        time.sleep(1)
