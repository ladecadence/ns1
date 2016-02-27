#!/usr/bin/env python

import sys
import os
import pyaudio
import wave
import time
import datetime
import RPi.GPIO as GPIO

import gsbcgps


############ CONFIGURATION ############

# ID
ID="EA1IDZ"
SUBID="NS1"

# pins
PTT_PIN=14
VFO_PIN=5

# delays
APRS_REPEAT=5
APRS_DELAY=10

# wave buffer
CHUNK=128

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
raspistill_cmd = "/usr/bin/raspistill -t 1 -e png " 
convert_cmd = "/usr/bin/convert "
mogrify_cmd = "/usr/bin/mogrify "
pisstv_cmd = "pisstvpp/pisstvpp -pr36 -r44100 "

# playback
play_cmd = "/usr/bin/aplay "

######################################################

# GPS
gps = gsbcgps.GsbcGPS(gsbcgps.SERIAL_PORT, gsbcgps.SERIAL_SPEED)
voltage = "11.8"

# Set GPIOs
GPIO.setmode(GPIO.BCM)
GPIO.setup(PTT_PIN, GPIO.OUT) 
GPIO.setup(VFO_PIN, GPIO.OUT)



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

def gen_sstv_file():
    # take picture
    hour_date = datetime.datetime.now()
    hour_date = "%d-%d-%d_%d:%d" % (hour_date.day, hour_date.month, \
	hour_date.year, hour_date.hour, hour_date.minute)
    
    pic_name = pics_dir + "sstvpic_" + hour_date + ".png"
    print os.system(raspistill_cmd + "-o " + pic_name)

    # generate 320x256 picture
    print os.system(convert_cmd + pic_name + " -resize 320x256 " + sstv_png)

    # add ID and date to the picture
    print os.system(mogrify_cmd + "-fill white -pointsize 24 -draw " + \
            "\"text 10,40 '" + ID + "'\" " + sstv_png)
    print os.system(mogrify_cmd + "-pointsize 24 -draw " + \
            "\"text 12,42 '" + ID + "'\" " + sstv_png)
    print os.system(mogrify_cmd + "-pointsize 14 -draw " + \
            "\"text 10,60 '" + hour_date + "'\" " + sstv_png)
    print os.system(mogrify_cmd + "-fill white -pointsize 14 -draw " + \
            "\"text 11,61 '" + hour_date + "'\" " + sstv_png)
    
    # generate sound file
    print os.system(pisstv_cmd + sstv_png)

def gen_aprs_file():
    # get data from GPS and sensors
    #gps.update()
    # generate APRS format coordinates
    coords = "%07.2f%s/%08.2f%s" % (float(gps.latitude), gps.ns, float(gps.longitude), gps.ew)

    if gps.heading == "":
        hdg = "0"
    else:
        hdg=str(gps.heading)

    # create APRS message file
    aprs_msg = ID + "-11>WORLD,WIDE2-2:!" + coords + "O" + hdg + "/" + \
            str(gps.speed) + "/A=" + str(gps.altitude) + "/V=" + str(voltage) + "\n"
    
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
        change_vfo()
        gen_sstv_file()
        ptt_on()
        play_sstv()
        ptt_off()
        change_vfo()
        time.sleep(5)

