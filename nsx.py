#!/usr/bin/env python3

import sys
import os
import time
import datetime
import configparser
import RPi.GPIO as GPIO

import ashabgps
import mcp3002
import ms5607
import ds18b20
import log
import pyRF95.rf95 as rf95
import led
import image

######################################################
# Globals

# ascension rate
last_ascension_rate_time = 0
# last altitude
last_altitude = 0

# counter for SSDV images sent
ssdv_image_num = 0

######################################################
# OBJECTS

# log
debug_log = None

# GPS
gps = None

# ADC
adc = None

# temperature sensors
ds18b20_int = None
ds18b20_ext = None

# barometer
baro = None

# led
status_led = None

# Images
pictures = None

######################################################
# Functions

def read_voltage():
    # Enable voltage divider
    GPIO.output(BATT_EN_PIN, True)
    time.sleep(0.1)
    # adc value
    adc_value=adc.read(VOLT_ADC)
    # disable it
    GPIO.output(BATT_EN_PIN, False)

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

def gen_ssdv_file():
    # take picture
    pic_name = pictures.take()
    
    if pic_name == None:
        debug_log.log(log.LogType.ERR, "Problem taking picture")
        return None

    debug_log.log(log.LogType.INFO, "Took picture: " + pic_name)

    # generate resized picture
    stat = pictures.resize(SSDV_SIZE, pic_name, SSDV_NAME)

    if stat == None:
        debug_log.log(log.LogType.ERR, "Problem resizing picture")
        return None
    
    debug_log.log(log.LogType.INFO, "Resized picture: " + pic_name)
    
    # add ID and date to the picture
    stat = pictures.add_info(SSDV_NAME, ID + SUBID, MSG)
    if stat == None:
        debug_log.log(log.LogType.ERR, "Problem adding info to picture")
        return None
    
    debug_log.log(log.LogType.INFO, "Added info to picture: " + SSDV_NAME)
      
    # SSDV
    stat = pictures.gen_ssdv(SSDV_NAME, ID, ssdv_image_num)
    if stat == None:
        debug_log.log(log.LogType.ERR, "Problem generating SSDV file")
        return None

    debug_log.log(log.LogType.INFO, "Generated SSDV binary file")

    return stat

def send_ssdv_image():
    global ssdv_image_num
    ssdv_filename = IMAGES_DIR + SSDV_NAME + ".bin"
    try:
        ssdv_file = open(ssdv_filename, "rb")
    except IOError as e:
        debug_log.log(log.LogType.ERR, "Problem opening SSDV picture: " + str(e))
        return

    if os.path.getsize(ssdv_filename)%256 != 0:
        debug_log.log(log.LogType.ERR, "File does not look like a SSDV image")
        return

    # ok, get number of packets to send
    ssdv_packets = os.path.getsize(ssdv_filename)//256

    debug_log.log(log.LogType.INFO, "Sending SSDV Image #" + str(ssdv_image_num))
    # Send ssdv packets
    # We are ignoring the first sync byte of each packet
    # as the rf95 packet payload size is just 255 bytes.
    # We need to take this into account on the receive side.
    for i in range(ssdv_packets):
        ssdv_file.seek((i*256)+1, 0)
        rf95.send(rf95.bytes_to_data(ssdv_file.read(255)))
        status_led.blink()
        time.sleep(0.5)                 # processing time
        rf95.wait_packet_sent()
    # Done
    rf95.set_mode_idle()
    ssdv_file.close()
    
    debug_log.log(log.LogType.INFO, "Sent " + str(ssdv_packets) + " packets from SSDV Image #" + str(ssdv_image_num))

    ssdv_image_num = ssdv_image_num + 1


def gen_telemetry():
    # get data from GPS and sensors
    hour_date = datetime.datetime.now()
    hour_date = SEPARATOR + "%02d-%02d-%d" % (hour_date.day, \
            hour_date.month, hour_date.year) + SEPARATOR + \
            "%02d:%02d:%02d" % (hour_date.hour, \
            hour_date.minute, hour_date.second)
    gps.update()
    debug_log.log(log.LogType.DATA, "NMEA: " + gps.line_gga.strip())
    voltage = read_voltage()
    debug_log.log(log.LogType.DATA, "BATT: " + str(voltage))
    ascension_rate = get_ascension_rate()
    try:
        baro.update()
        baro_pressure = baro.get_pres()
        debug_log.log(log.LogType.DATA, "BARO: " + str(baro_pressure))
        baro_altitude = baro.get_alt()
        debug_log.log(log.LogType.DATA, "BALT: " + str(baro_altitude))
        baro_temp = baro.get_temp()
        debug_log.log(log.LogType.DATA, "BTEMP: " + str(baro_temp))
    except Exception as e:
        debug_log.log(log.LogType.ERR, "Problem with barometer, using default values : " + str(e))
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
    #aprs_msg = ID + "-11>WORLD,WIDE2-2:!" + coords + "O" + \
    aprs_msg = "$$" + ID + "!" + coords + "O" + \
            str(gps.heading) + SEPARATOR + \
            str(gps.speed) + SEPARATOR + "A=" + str(gps.altitude) + \
            SEPARATOR + "V=" + "%.2f" % voltage + SEPARATOR + "P=" + \
            "%.1f" % (baro_pressure) + SEPARATOR + \
            "TI=" + "%.2f" % temp_int + SEPARATOR + "TO=" + \
            "%.2f" % temp_ext + hour_date + SEPARATOR + "GPS=" + \
            "%09.6f%s,%010.6f%s" % (gps.decimal_latitude(), gps.ns , \
            gps.decimal_longitude(), gps.ew) + SEPARATOR + \
            "SATS=" + str(gps.sats) + SEPARATOR + "AR=" + \
            "%.2f" % ascension_rate
    if MSG:
        aprs_msg = aprs_msg + SEPARATOR + MSG.replace("\n", " - ") \
                + "\n"
    else:
        aprs_msg = aprs_msg + "\n"


    # message is 255 bytes (same as SSDV)
    if len(aprs_msg) < 255:
        # append zeros
        while len(aprs_msg) < 255:
            aprs_msg = aprs_msg + "\0"


    return aprs_msg

def cleanup():
    GPIO.cleanup()

######################### MAIN ##############################

if __name__ == "__main__":

    # Read and parse configuration
    try:
        config = configparser.ConfigParser()
        config.read('nsx.cfg')
    except Exception as e:
        # create an emergency log
        debug_log = log.Log("/tmp/nsx-emergency.log")
        debug_log.log(log.LogType.ERR, "Unable to open the configuration file: " + str(e))
        quit(1)

    # ok, get config values
    try: 
        # Mission
        ID = config.get("mission", "id")
        SUBID = config.get("mission", "subid")
        MSG = config.get("mission", "msg")
        SEPARATOR = config.get("mission", "separator")
        TELEM_REPEAT = config.getint("mission", "packet_repeat")
        TELEM_DELAY = config.getint("mission", "packet_delay")

        # GPIO
        BATT_EN_PIN = config.getint("gpio", "batt_enable_pin")
        LED_PIN = config.getint("gpio", "led_pin")
        
        # GPS
        GPS_SERIAL = config.get("gps", "serial_port")
        GPS_SPEED = config.getint("gps", "speed")

        # LoRa
        RF95_CS = config.getint("lora", "cs")
        RF95_INT = config.getint("lora", "int_pin")
        RF95_FREQ = config.getfloat("lora", "freq")
        RF95_PWR = config.getint("lora", "low_pwr")
        RF95_HPWR = config.getint("lora", "high_pwr")

        # ADC
        ADC_CS = config.getint("adc", "cs")
        VOLT_ADC = config.getint("adc", "vbatt")
        VOLT_DIVIDER = config.getfloat("adc", "v_divider")
        VOLT_MULTIPLIER = config.getfloat("adc", "v_mult")

        # temperature sensors
        TEMP_INT_ADDR = config.get("temp", "internal_addr")
        TEMP_EXT_ADDR = config.get("temp", "external_addr")

        # barometer
        BARO_I2C_BUS = config.getint("baro", "i2c_bus")
        BARO_I2C_ADDR = int(config.get("baro", "i2c_addr"), 16)

        # paths
        DIRECTORY = config.get("paths", "main_dir")
        IMAGES_DIR = config.get("paths", "images_dir")
        LOG_FILE = config.get("paths", "log")

        # SSDV
        SSDV_SIZE = config.get("ssdv", "size")
        SSDV_NAME = config.get("ssdv", "name")
    except Exception as e:
         # create an emergency log
        debug_log = log.Log("/tmp/nsx-emergency.log")
        debug_log.log(log.LogType.ERR, "Unable to parse the configuration file: " + str(e))
        quit(1)

    # Ok, create objects

    # log
    debug_log = log.Log(LOG_FILE)
    # init logging
    debug_log.reset()

    # GPS
    gps = ashabgps.AshabGPS(GPS_SERIAL, GPS_SPEED)

    # LoRa
    rf95 = rf95.RF95(RF95_CS, RF95_INT)

    # ADC
    adc = mcp3002.Mcp3002(ADC_CS)

    # temperature sensors
    ds18b20_int = ds18b20.Ds18b20(TEMP_INT_ADDR)
    ds18b20_ext = ds18b20.Ds18b20(TEMP_EXT_ADDR)

    # barometer
    baro = ms5607.MS5607(BARO_I2C_BUS, BARO_I2C_ADDR)
    try:
        baro.read_prom()
    except Exception as e:
        debug_log.log(log.LogType.ERR, "Problem with barometer: " + str(e))

    # led
    status_led = led.LED(LED_PIN)

    # Images
    pictures = image.Image(IMAGES_DIR)


    # be sure that the pictures drive is mounted
    # mount = os.system("udisks --mount /dev/sda1")
    # debug_log.log(log.LogType.INFO, "Mounting pendrive: " + str(mount))

    # Set GPIOs
    GPIO.setmode(GPIO.BCM)

    GPIO.setup(BATT_EN_PIN, GPIO.OUT)
    GPIO.output(BATT_EN_PIN, False)

    # initial time
    # get time from gps
    gps.update()
    hours, mins, secs = gps.get_time()
    # set system time
    if hours!="" and mins!="" and secs!="":
        stat = gps.set_system_time()
        debug_log.log(log.LogType.INFO, "System clock set: " + str(stat))

    last_ascension_rate_time = datetime.datetime.now()

    debug_log.log(log.LogType.INFO, "Starting...")

    # init radio
    if not rf95.init():
        debug_log.log(log.LogType.ERR, "RF95 not found")
        status_led.err()
        cleanup()
        quit(1)
    else:
        debug_log.log(log.LogType.INFO, "RF95 LoRa mode ok")

    # set frequency and power
    rf95.set_frequency(RF95_FREQ)
    rf95.set_tx_power(RF95_PWR)

    while 1:
        # send telemetry packet
        for i in range(TELEM_REPEAT):
            telem_str = gen_telemetry()
            rf95.send(rf95.str_to_data(telem_str))
            rf95.wait_packet_sent()
            status_led.blink()
            debug_log.log(log.LogType.INFO, "LoRa Telemetry packet sent")
            debug_log.log(log.LogType.INFO, telem_str)
            # wait X secs
            time.sleep(TELEM_DELAY)

        # send ssdv image
        if gen_ssdv_file() != None:
            send_ssdv_image()
            time.sleep(5)

