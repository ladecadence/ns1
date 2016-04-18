#!/usr/bin/env python

import sys
import os
import pyaudio
import wave
import time
import datetime
import RPi.GPIO as GPIO
import Adafruit_BMP.BMP085 as BMP085

import gsbcgps
import mcp3008
import ds18b20

############ CONFIGURATION ############

# ID
ID="EA1IDZ"
SUBID="/NS1"

# Test
TEST_MSG1="EA1IDZ test baliza APRS/SSTV"
TEST_MSG2="ea1idz@ladecadence.net"
TEST_MSG=True

# pins
PTT_PIN=22	# PIN 15
VFO_PIN=27	# PIN 13
SPI_CLK=11
SPI_MISO=9
SPI_MOSI=10
SPI_CE0=8
BATT_EN_PIN=25

# GPS
GPS_SERIAL = "/dev/ttyAMA0"
GPS_SPEED = 9600

# delays
APRS_REPEAT=10
APRS_DELAY=10

# voltage ADC channel
VOLT_ADC = 0
# voltage correction
VOLT_MULTIPLIER = 1

# temperature sensors
TEMP_INT_ADDR = "28-0000079ee65f"
TEMP_EXT_ADDR = ""

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
#pics_dir = directory + "pictures/"
pics_dir = "/media/GSBC-PICS/"
raspistill_cmd = "/usr/bin/raspistill -t 1 -e png " 
convert_cmd = "/usr/bin/convert "
mogrify_cmd = "/usr/bin/mogrify "
pisstv_cmd = "pisstvpp/pisstvpp -pr36 -r44100 "

# playback
play_cmd = "/usr/bin/aplay "

######################################################

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
    # voltage divisor is 1/2 at 3.3V, 10bit ADC so
    v = VOLT_MULTIPLIER * 2 * (adc_value*3.3/1023.0)
    return v

def gen_sstv_file():
    # take picture
    hour_date = datetime.datetime.now()
    hour_date = "%02d-%02d-%d_%02d_%02d" % (hour_date.day, hour_date.month, \
	hour_date.year, hour_date.hour, hour_date.minute)
    
    pic_name = pics_dir + "sstvpic_" + hour_date + ".png"
    print os.system(raspistill_cmd + "-o " + pic_name)

    # generate 320x256 picture
    print os.system(convert_cmd + pic_name + " -resize 320x256 " + sstv_png)

    # add ID and date to the picture
    print os.system(mogrify_cmd + "-fill white -pointsize 24 -draw " + \
            "\"text 10,40 '" + ID + SUBID + "'\" " + sstv_png)
    print os.system(mogrify_cmd + "-pointsize 24 -draw " + \
            "\"text 12,42 '" + ID + SUBID + "'\" " + sstv_png)
    print os.system(mogrify_cmd + "-pointsize 14 -draw " + \
            "\"text 10,60 '" + hour_date + "'\" " + sstv_png)
    print os.system(mogrify_cmd + "-fill white -pointsize 14 -draw " + \
            "\"text 11,61 '" + hour_date + "'\" " + sstv_png)
    
    if TEST_MSG:
    	print os.system(mogrify_cmd + "-fill black -pointsize 18 -draw " + \
            "\"text 10,85 '" + TEST_MSG1 + "'\" " + sstv_png)
    	print os.system(mogrify_cmd + "-fill white -pointsize 18 -draw " + \
            "\"text 11,86 '" + TEST_MSG1 + "'\" " + sstv_png)
    	print os.system(mogrify_cmd + "-fill black -pointsize 18 -draw " + \
            "\"text 10,105 '" + TEST_MSG2 + "'\" " + sstv_png)
    	print os.system(mogrify_cmd + "-fill white -pointsize 18 -draw " + \
            "\"text 11,106 '" + TEST_MSG2 + "'\" " + sstv_png)
 

    # generate sound file
    print os.system(pisstv_cmd + sstv_png)

def gen_aprs_file():
    # get data from GPS and sensors
    gps.update()
    voltage = read_voltage()
    baro_pressure = baro.read_pressure()
    baro_altitude = baro.read_altitude()
    baro_temp = baro.read_temperature()
    temp_int = ds18b20_int.read()
    hour_date = datetime.datetime.now()
    hour_date = "/%02d-%02d-%d/%02d:%02d" % (hour_date.day, hour_date.month, \
	hour_date.year, hour_date.hour, hour_date.minute)
    

    # generate APRS format coordinates
    try:
	    coords = "%07.2f%s/%08.2f%s" % (float(gps.latitude), gps.ns, float(gps.longitude), gps.ew)
    except:
		coords = "XXXX.XX/XXXXX.XX"

    if gps.heading == "":
        hdg = "0"
    else:
        hdg=str(gps.heading)

    # create APRS message file
    aprs_msg = ID + "-11>WORLD,WIDE2-2:!" + coords + "O" + hdg + "/" + \
            str(gps.speed) + "/A=" + str(gps.altitude) + "/V=" + "%.2f" % voltage + \
	    "/P=" + "%.1f" % (baro_pressure/100) + "/TI=" + "%.2f" % temp_int + \
	    "/TO=" + "%.2f" % baro_temp + hour_date + "/LAT=" + gps.latitude + \
	    gps.ns + "/LON=" + gps.longitude + gps.ew
    if TEST_MSG:
	aprs_msg = aprs_msg + "/" + TEST_MSG1 + " " + TEST_MSG2 + "\n"
    else:
	aprs_msg = aprs_msg + "\n"
    
    print aprs_msg
    f = open(aprs_data, 'w')
    f.write(aprs_msg)
    f.close()

    # create APRS wav file
    print os.system(gen_pkt_cmd + " -o " + aprs_wav + " " + aprs_data)
    
# play commands
def play_aprs():
    print os.system(play_cmd + aprs_wav)
    
def play_sstv():
    print os.system(play_cmd + sstv_wav)

######################### MAIN ##############################

if __name__ == "__main__":

	# be sure that the pictures drive is mounted
	os.system("udisks --mount /dev/sda1")	

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

