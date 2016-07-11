#!/usr/bin/env python

import sys
import os
import pyaudio
import wave
import time
import datetime
import RPi.GPIO as GPIO
import Adafruit_BMP.BMP085 as BMP085
import logging

import gsbcgps
import mcp3008
import ds18b20

############ CONFIGURATION ############

# ID
ID="EA1IDZ"
SUBID="/NS1"

# Test
TEST_MSG1="ASHAB High Altitude Balloon NS2"
TEST_MSG2="info@ashab.space "
TEST_MSG=True

# pins
PTT_PIN=22      # PIN 15
VFO_PIN=27      # PIN 13
SPI_CLK=11
SPI_MISO=9
SPI_MOSI=10
SPI_CE0=8
BATT_EN_PIN=25

# Field separator
SEPARATOR = "/"

# GPS
GPS_SERIAL = "/dev/ttyUSB0"
GPS_SPEED = 9600

# delays
APRS_REPEAT=20
APRS_DELAY=26

# voltage ADC channel
VOLT_ADC = 0
# voltage correction
VOLT_DIVIDER = 3.2
VOLT_MULTIPLIER = 1

# temperature sensors
TEMP_INT_ADDR = "28-0000079ee65f"
TEMP_EXT_ADDR = "28-0000079e9f12"

# FILES AND PROGRAMS

# directory END SLASH!!!
directory = "/home/pi/gsbc/"

# sstv wav file
sstv_png = directory + "sstv.png"
sstv_wav = directory + "sstv.png.wav"

# aprs files
aprs_data = directory + "aprs.dat"
aprs_wav = directory + "aprs.wav"

# direwolf gen_packet command
gen_pkt_cmd = directory + "direwolf/gen_packets"

# snapsstv
pics_dir = directory + "pictures/"
# pics_dir = "/media/GSBC-PICS/"
raspistill_cmd = "/usr/bin/raspistill -t 1 -ISO 100 -e png "
convert_cmd = "/usr/bin/convert "
mogrify_cmd = "/usr/bin/mogrify "
pisstv_cmd = "pisstvpp/pisstvpp -pr36 -r44100 "

# playback
play_cmd = "/usr/bin/aplay "

######################################################

# logging
log_file = directory + "log.txt"

# GPS
gps = gsbcgps.GsbcGPS(GPS_SERIAL, GPS_SPEED)

# Set GPIOs
GPIO.setmode(GPIO.BCM)

GPIO.setup(PTT_PIN, GPIO.OUT)
GPIO.output(PTT_PIN, False)

GPIO.setup(VFO_PIN, GPIO.OUT)
GPIO.output(VFO_PIN, False)

GPIO.setup(BATT_EN_PIN, GPIO.OUT)
GPIO.output(BATT_EN_PIN, False)

# ADC
adc = mcp3008.Mcp3008(SPI_CLK, SPI_MOSI, SPI_MISO, SPI_CE0)

# Barometer
baro = BMP085.BMP085(mode=BMP085.BMP085_HIGHRES)

# temperature sensors
ds18b20_int = ds18b20.Ds18b20(TEMP_INT_ADDR)
ds18b20_ext = ds18b20.Ds18b20(TEMP_EXT_ADDR)

# ascension rate
# aprs packet time
last_ascension_rate_time = 0
# last altitude
last_altitude = 0

######################################################

def ptt_on():
    GPIO.output(PTT_PIN, True)
    time.sleep(1)
def ptt_off():
    GPIO.output(PTT_PIN, False)
    time.sleep(1)

def change_vfo():
    GPIO.output(VFO_PIN, True)
    time.sleep(0.1)
    GPIO.output(VFO_PIN, False)

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
        logging.info("DEBUG: ASR -> Tdelta: " + str(delta_time.seconds) + " alt-dif : " + str(float(gps.altitude) - last_altitude))
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
        logging.info("DEBUG: taking picture: " + str(stat))

        # generate 320x256 picture
        stat =  os.system(convert_cmd + pic_name + \
                " -resize 320x256 " + sstv_png)
        logging.info("DEBUG: resize picture: " + str(stat))

        # add ID and date to the picture
        stat = os.system(mogrify_cmd + \
                "-fill white -pointsize 24 -draw " + \
                "\"text 10,40 '" + ID + SUBID + "'\" " + sstv_png)
        logging.info("DEBUG: Add ID 1: " + str(stat))
        stat =  os.system(mogrify_cmd + \
                "-pointsize 24 -draw " + \
                "\"text 12,42 '" + ID + SUBID + "'\" " + sstv_png)
        logging.info("DEBUG: Add ID 2: " + str(stat))
        stat =  os.system(mogrify_cmd + \
                "-pointsize 14 -draw " + \
                "\"text 10,60 '" + hour_date + "'\" " + sstv_png)
        logging.info("DEBUG: Add Date 1: " + str(stat))
        stat =  os.system(mogrify_cmd + \
                "-fill white -pointsize 14 -draw " + \
                "\"text 11,61 '" + hour_date + "'\" " + sstv_png)
        logging.info("DEBUG: Add Date 2: " + str(stat))

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
            logging.info("DEBUG: Add test MSG: " + str(stat))
    except:
        logging.info("ERROR: Problem taking picture")


    # generate sound file
    stat =  os.system(pisstv_cmd + sstv_png)
    logging.info("DEBUG: Generate SSTV Audio: " + str(stat))

def gen_aprs_file():
    # get data from GPS and sensors
    hour_date = datetime.datetime.now()
    hour_date = SEPARATOR + "%02d-%02d-%d" % (hour_date.day, \
            hour_date.month, hour_date.year) + SEPARATOR + \
            "%02d:%02d:%02d" % (hour_date.hour, \
            hour_date.minute, hour_date.second)
    gps.update()
    logging.info("DATA: NMEA: " + gps.line_gga)
    voltage = read_voltage()
    logging.info("DATA: BATT: " + str(voltage))
    ascension_rate = get_ascension_rate()
    try:
        baro_pressure = baro.read_pressure()
        logging.info("DATA: BARO: " + str(baro_pressure))
        baro_altitude = baro.read_altitude()
        logging.info("DATA: BALT: " + str(baro_altitude))
        baro_temp = baro.read_temperature()
        logging.info("DATA: BTEMP: " + str(baro_temp))
    except:
        logging.warn("ERROR: Problem with barometer, using default values")
        baro_pressure = 1013.2
        baro_altitude = 0
        baro_temp = 15
    temp_int = ds18b20_int.read()
    temp_ext = ds18b20_ext.read()
    logging.info("DATA: Tin: " + str(temp_int))
    logging.info("DATA: Tout: " + str(temp_ext))

    # generate APRS format coordinates
    try:
        coords = "%07.2f%s" % (float(gps.latitude), gps.ns)  \
                + SEPARATOR + \
                "%08.2f%s" % (float(gps.longitude), gps.ew)
    except:
        logging.warning("ERROR: GPS: " + gps.latitude + " " + \
            gps.longitude)
        coords = "0000.00N" + SEPARATOR + "00000.00W"

    logging.info("DATA: LAT: " + gps.latitude)
    logging.info("DATA: LON: " + gps.longitude)
    logging.info("DATA: ALT: " + str(gps.altitude))

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

    print (aprs_msg)
    f = open(aprs_data, 'w')
    f.write(aprs_msg)
    f.close()

    # create APRS wav file
    stat =  os.system(gen_pkt_cmd + " -o " + aprs_wav + " " + aprs_data)
    logging.info("DEBUG: Created APRS wav: " + str(stat))

# play commands
def play_aprs():
    stat = os.system(play_cmd + aprs_wav)
    logging.info("DEBUG: Played APRS wav: " + str(stat))
    logging.info(" ")

def play_sstv():
    stat = os.system(play_cmd + sstv_wav)
    logging.info("DEBUG: Played SSTV wav: " + str(stat))
    logging.info(" ")

######################### MAIN ##############################

if __name__ == "__main__":

    # init logging
    logging.basicConfig(filename=log_file, level=logging.INFO, \
            format='%(asctime)s %(message)s', \
            datefmt='%d/%m/%Y %I:%M:%S %p')

    # be sure that the pictures drive is mounted
    # mount = os.system("udisks --mount /dev/sda1")
    # logging.info("DEBUG: Mounting pendrive: " + str(mount))

    # initial time
    last_ascension_rate_time = datetime.datetime.now()

    while 1:
        # each minute send APRS packet
        for i in range(APRS_REPEAT):
            gen_aprs_file()
            ptt_on()
            play_aprs()
            ptt_off()
            # wait X secs
            time.sleep(APRS_DELAY)

        # send sstv image
        #change_vfo()
        gen_sstv_file()
        ptt_on()
        play_sstv()
        ptt_off()
        #change_vfo()
        time.sleep(5)
