#!/usr/bin/env python3

import sys
import os
import time
import datetime
import RPi.GPIO as GPIO

import ashabgps
import mcp3008
import ds18b20
import log

############ CONFIGURATION ############

# ID
ID="EA1IDZ"
SUBID="/NSX"

# Test
TEST_MSG1="ASHAB High Altitude Balloon NSX"
TEST_MSG2="info@ashab.space "
TEST_MSG=True

# pins
SPI_CLK=11
SPI_MISO=9
SPI_MOSI=10
SPI_CE0=8
BATT_EN_PIN=24

# Field separator
SEPARATOR = "/"

# GPS
GPS_SERIAL = "/dev/ttyAMA0"
GPS_SPEED = 9600

# delays
TELEM_REPEAT=20
TELEM_DELAY=30

# voltage ADC channel
VOLT_ADC = 0
# voltage correction
VOLT_DIVIDER = 3.2
VOLT_MULTIPLIER = 1

# temperature sensors
TEMP_INT_ADDR = "28-031682a91bff"
TEMP_EXT_ADDR = "28-0000079e9f12"

# FILES AND PROGRAMS

# directory END SLASH!!!
directory = "/home/pi/ASHAB/"

# sstv file
sstv_png = directory + "sstv.png"

# snapsstv
pics_dir = directory + "pictures/"
# pics_dir = "/media/GSBC-PICS/"
raspistill_cmd = "/usr/bin/raspistill -t 1 -ISO 100 -e png "
convert_cmd = "/usr/bin/convert "
mogrify_cmd = "/usr/bin/mogrify "
pisstv_cmd = "pisstvpp/pisstvpp -pr36 -r44100 "

# logging
log_file = directory + "log.txt"

# log
debug_log = log.Log(log_file)

######################################################

# GPS
gps = ashabgps.AshabGPS(GPS_SERIAL, GPS_SPEED)

# Set GPIOs
GPIO.setmode(GPIO.BCM)

GPIO.setup(BATT_EN_PIN, GPIO.OUT)
GPIO.output(BATT_EN_PIN, False)

# ADC
adc = mcp3008.Mcp3008(SPI_CLK, SPI_MOSI, SPI_MISO, SPI_CE0)

# temperature sensors
ds18b20_int = ds18b20.Ds18b20(TEMP_INT_ADDR)
ds18b20_ext = ds18b20.Ds18b20(TEMP_EXT_ADDR)

# ascension rate
# aprs packet time
last_ascension_rate_time = 0
# last altitude
last_altitude = 0

######################################################

def read_voltage():
    # adc value
    adc_value=adc.read(VOLT_ADC)
    # voltage divisor at 3.3V, 10bit ADC so
    v = VOLT_MULTIPLIER * VOLT_DIVIDER * (adc_value*3.3/1023.0)
    return v

def get_ascension_rate():
    global last_altitude
    global last_ascension_rate_time

    # get current time
    now = datetime.datetime.now()
    # while we have default altitude (no GPS)
    if last_altitude == 0:
        try:
            last_altitude = float(gps.altitude)
            last_ascension_rate_time = now
            return 0
        except ValueError:
            last_altitude = 0
            last_ascension_rate_time = now
            return 0

    # else calculate ascension rate
    try:
        delta_time = now - last_ascension_rate_time
        asc_rate = (float(gps.altitude) - last_altitude) / delta_time.seconds
        debug_log.log(log.LogType.INFO, \
		"ASR -> Tdelta: " + str(delta_time.seconds) + 
		" alt-dif : " + str(float(gps.altitude) - last_altitude))
        last_ascension_rate_time = now
        last_altitude = float(gps.altitude)
        return asc_rate
    except ValueError:
        last_ascension_rate_time = now
        return 0

def gen_sstv_file():
    # take picture
    hour_date = datetime.datetime.now()
    hour_date = "%02d-%02d-%d_%02d_%02d" % (hour_date.day, \
            hour_date.month, hour_date.year, hour_date.hour, \
            hour_date.minute)

    try:
        pic_name = pics_dir + "sstvpic_" + hour_date + ".png"
        stat =  os.system(raspistill_cmd + "-o " + pic_name)
        debug_log.log(log.LogType.INFO, "taking picture: " + str(stat))

        # generate 320x256 picture
        stat =  os.system(convert_cmd + pic_name + \
                " -resize 320x256 " + sstv_png)
        debug_log.log(log.LogType.INFO, "resize picture: " + str(stat))

        # add ID and date to the picture
        stat = os.system(mogrify_cmd + \
                "-fill white -pointsize 24 -draw " + \
                "\"text 10,40 '" + ID + SUBID + "'\" " + sstv_png)
        debug_log.log(log.LogType.INFO, "Add ID 1: " + str(stat))
        stat =  os.system(mogrify_cmd + \
                "-pointsize 24 -draw " + \
                "\"text 12,42 '" + ID + SUBID + "'\" " + sstv_png)
        debug_log.log(log.LogType.INFO, "Add ID 2: " + str(stat))
        stat =  os.system(mogrify_cmd + \
                "-pointsize 14 -draw " + \
                "\"text 10,60 '" + hour_date + "'\" " + sstv_png)
        debug_log.log(log.LogType.INFO, "Add Date 1: " + str(stat))
        stat =  os.system(mogrify_cmd + \
                "-fill white -pointsize 14 -draw " + \
                "\"text 11,61 '" + hour_date + "'\" " + sstv_png)
        debug_log.log(log.LogType.INFO, "Add Date 2: " + str(stat))

        if TEST_MSG:
            stat =  os.system(mogrify_cmd + \
                    "-fill black -pointsize 18 -draw " + \
                    "\"text 10,85 '" + TEST_MSG1 + "'\" " + sstv_png)
            stat =  os.system(mogrify_cmd + \
                    "-fill white -pointsize 18 -draw " + \
                    "\"text 11,86 '" + TEST_MSG1 + "'\" " + sstv_png)
            stat =  os.system(mogrify_cmd + \
                    "-fill black -pointsize 18 -draw " + \
                    "\"text 10,105 '" + TEST_MSG2 + "'\" " + sstv_png)
            stat =  os.system(mogrify_cmd + \
                    "-fill white -pointsize 18 -draw " + \
                    "\"text 11,106 '" + TEST_MSG2 + "'\" " + sstv_png)
            debug_log.log(log.LogType.INFO, "Add test MSG: " + str(stat))
    except:
        debug_log.log(log.LogType.ERR, "Problem taking picture")


def gen_telemetry():
    # get data from GPS and sensors
    hour_date = datetime.datetime.now()
    hour_date = SEPARATOR + "%02d-%02d-%d" % (hour_date.day, \
            hour_date.month, hour_date.year) + SEPARATOR + \
            "%02d:%02d:%02d" % (hour_date.hour, \
            hour_date.minute, hour_date.second)
    gps.update()
    debug_log.log(log.LogType.DATA, "NMEA: " + gps.line_gga)
    voltage = read_voltage()
    debug_log.log(log.LogType.DATA, "BATT: " + str(voltage))
    ascension_rate = get_ascension_rate()
    try:
        baro_pressure = baro.read_pressure()
        debug_log.log(log.LogType.DATA, "BARO: " + str(baro_pressure))
        baro_altitude = baro.read_altitude()
        debug_log.log("log.LogType.DATA, BALT: " + str(baro_altitude))
        baro_temp = baro.read_temperature()
        debug_log.log(log.LogType.DATA, "BTEMP: " + str(baro_temp))
    except:
        debug_log.log(log.LogType.ERR, "Problem with barometer, using default values")
        baro_pressure = 1013.2
        baro_altitude = 0
        baro_temp = 15
    temp_int = ds18b20_int.read()
    temp_ext = ds18b20_ext.read()
    debug_log.log(log.LogType.DATA, "Tin: " + str(temp_int))
    debug_log.log(log.LogType.DATA, "Tout: " + str(temp_ext))

    # generate APRS format coordinates
    try:
        coords = "%07.2f%s" % (float(gps.latitude), gps.ns)  \
                + SEPARATOR + \
                "%08.2f%s" % (float(gps.longitude), gps.ew)
    except:
        debug_log.log(log.LogType.ERR, "GPS: " + gps.latitude + " " + \
            gps.longitude)
        coords = "0000.00N" + SEPARATOR + "00000.00W"

    debug_log.log(log.LogType.DATA, "LAT: " + gps.latitude)
    debug_log.log(log.LogType.DATA, "LON: " + gps.longitude)
    debug_log.log(log.LogType.DATA, "ALT: " + str(gps.altitude))

    # create APRS message file
    aprs_msg = ID + "-11>WORLD,WIDE2-2:!" + coords + "O" + \
            str(gps.heading) + SEPARATOR + \
            str(gps.speed) + SEPARATOR + "A=" + str(gps.altitude) + \
            SEPARATOR + "V=" + "%.2f" % voltage + SEPARATOR + "P=" + \
            "%.1f" % (baro_pressure/100) + SEPARATOR + \
            "TI=" + "%.2f" % temp_int + SEPARATOR + "TO=" + \
            "%.2f" % temp_ext + hour_date + SEPARATOR + "GPS=" + \
            "%09.6f%s,%010.6f%s" % (gps.decimal_latitude(), gps.ns , \
            gps.decimal_longitude(), gps.ew) + SEPARATOR + \
            "SATS=" + str(gps.sats) + SEPARATOR + "AR=" + \
            "%.2f" % ascension_rate
    if TEST_MSG:
        aprs_msg = aprs_msg + SEPARATOR + TEST_MSG1 + " " + TEST_MSG2 \
                + "\n"
    else:
        aprs_msg = aprs_msg + "\n"

    return aprs_msg

######################### MAIN ##############################

if __name__ == "__main__":

    # init logging
    debug_log.reset()

    # be sure that the pictures drive is mounted
    # mount = os.system("udisks --mount /dev/sda1")
    # debug_log.log(log.LogType.INFO, "Mounting pendrive: " + str(mount))

    # initial time
    last_ascension_rate_time = datetime.datetime.now()

    debug_log.log(log.LogType.INFO, "Starting...")

    while 1:
        # each minute send APRS packet
        for i in range(TELEM_REPEAT):
            gen_telemetry()
            # wait X secs
            time.sleep(TELEM_DELAY)

        # send sstv image
        gen_sstv_file()
        time.sleep(5)
