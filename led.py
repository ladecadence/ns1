# ASHAB.space 2017

import RPi.GPIO as GPIO
import time

# LED class, controls the status LED on the
# StratoZero Board. Debug and error blink patterns.
class LED:
    def __init__(self, pin):
        # Set GPIOs
        self.pin = pin
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, False)

    def blink(self):
        # standard blink
        GPIO.output(self.pin, True)
        time.sleep(0.2)
        GPIO.output(self.pin, False)

    
    def err(self):
        # 5 Fast blinks
        for i in range(5):
            GPIO.output(self.pin, True)
            time.sleep(0.1)
            GPIO.output(self.pin, False)
            time.sleep(0.1)

    def cleanup(self):
        GPIO.cleanup(self.pin)
