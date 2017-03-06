#!/usr/bin/env python3

# ASHAB.space 2017

import sys
import os
import time
import datetime


# module configuration
RASPISTILL = "/usr/bin/raspistill -t 1000 -st -e jpg "
CONVERT = "/usr/bin/convert "
MOGRIFY = "/usr/bin/mogrify "
SSTV = "pisstvpp/pisstvpp -pr36 -r44100 "
SSDV = "/home/pi/ASHAB/ssdv/ssdv -e -c " + "TEMPID" + " -i "

# Image class, takes pictures from the raspi camera and prepares them to be
# sent by radio.
class Image:
    # Output directory for the images
    def __init__(self, dir):
        self.pics_dir = dir
        if not self.pics_dir.endswith("/"):
            self.pics_dir = self.pics_dir + "/"

    # Takes a picture and saves it on the output directory
    # File name is date and time when the picture was taken
    # Returns pic name or None if there was an error
    def take(self):
        self.hour_date = datetime.datetime.now()
        self.hour_date = "%02d-%02d-%d_%02d_%02d" % (self.hour_date.day, \
                self.hour_date.month, self.hour_date.year, self.hour_date.hour, \
                self.hour_date.minute)

        try:
            pic_name = self.pics_dir + "pic_" + self.hour_date + ".jpg"
            stat =  os.system(RASPISTILL + "-o " + pic_name)
            if stat != 0:
                return None
            return pic_name

        except Exception as e:
            return None

    # Resizes picture, size is a string WIDTHxHEIGHT
    def resize(self, size, pic_name, resized_name):
        try:
            stat =  os.system(CONVERT + pic_name + \
                " -resize " + size + " " + self.pics_dir + resized_name)
            if stat != 0:
                return None
            return stat
        except Exception as e:
            return None

    # Adds info text to the pictures to be sent
    def add_info(self, name, ID, MSG):
        try:
            stat = os.system(MOGRIFY + \
                    "-fill white -pointsize 24 -draw " + \
                    "\"text 10,40 '" + ID + "'\" " + self.pics_dir + name)
            if stat != 0:
                return None
            stat =  os.system(MOGRIFY + \
                    "-pointsize 24 -draw " + \
                    "\"text 12,42 '" + ID + "'\" " + self.pics_dir + name)
            if stat != 0:
                return None
            stat =  os.system(MOGRIFY + \
                    "-pointsize 14 -draw " + \
                    "\"text 10,60 '" + self.hour_date + "'\" " + self.pics_dir + name)
            if stat != 0:
                return None
            stat =  os.system(MOGRIFY + \
                    "-fill white -pointsize 14 -draw " + \
                    "\"text 11,61 '" + self.hour_date + "'\" " + self.pics_dir + name)
            if stat != 0:
                return None
            
            if MSG != None:
                stat =  os.system(MOGRIFY + \
                    "-fill black -pointsize 18 -draw " + \
                    "\"text 10,85 '" + MSG + "'\" " + self.pics_dir + name)
                if stat != 0:
                    return None
                stat =  os.system(MOGRIFY + \
                    "-fill white -pointsize 18 -draw " + \
                    "\"text 11,86 '" + MSG + "'\" " + self.pics_dir + name)
                if stat != 0:
                    return None
            
            return stat

        except Exception as e:
            return None

    # Generates a SSDV binary file from the image passed
    def gen_ssdv(self, name, ID, num):
        try:
            cmd = SSDV.replace("TEMPID", ID)
            stat = os.system(cmd + \
                    str(num) + " " + \
                    self.pics_dir + name + " " + self.pics_dir + name + ".bin")
            if stat != 0:
                return None
            return stat
        except Exception as e:
            return None


# Test module if executed as a program
if __name__ == "__main__":
    pic = Image("/home/pi/tmp")
    picture_name = pic.take()
    if picture_name != None:
        print("Picture taken")
        stat = pic.resize("640x480", picture_name, "resized.jpg")
        if stat != None:
            print("Picture resized")
            stat = pic.add_info("resized.jpg", "TEST", "Test de mensaje\n123456789")
            if stat != None:
                print("Picture text added")
                stat = pic.gen_ssdv("resized.jpg", "EA1IDZ", 9)
                if stat != None:
                    print("SSDV generated")



 
           



        


