import RPi.GPIO as GPIO
import time

class LED:
    def __init__(self, pin):
        # Set GPIOs
        self.pin = pin
        GPIO.setmode(GPIO.BCM)

        GPIO.setup(self.pin, GPIO.OUT)
        GPIO.output(self.pin, False)

    def blink(self):
        GPIO.output(self.pin, True)
        time.sleep(0.2)
        GPIO.output(self.pin, False)

    
    def err(self):
        for i in range(5):
            GPIO.output(self.pin, True)
            time.sleep(0.01)
            GPIO.output(self.pin, False)
            time.sleep(0.01)

    def cleanup(self):
        GPIO.cleanup(self.pin)
