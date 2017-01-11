import RPi.GPIO as GPIO
import time

class Mcp3008:
	def __init__(self, clockpin, mosipin, misopin, cspin):
		self.clock = clockpin
		self.mosi = mosipin
		self.miso = misopin
		self.cs = cspin

		
		GPIO.setup(self.mosi, GPIO.OUT)
		GPIO.setup(self.miso, GPIO.IN)
		GPIO.setup(self.clock, GPIO.OUT)
		GPIO.setup(self.cs, GPIO.OUT)

	def read(self, adcnum):
		if ((adcnum > 7) or (adcnum < 0)):
			return -1
		GPIO.output(self.cs, True)
	 
		GPIO.output(self.clock, False)  # start clock low
		GPIO.output(self.cs, False)     # bring CS low
	 
		commandout = adcnum
		commandout |= 0x18  # start bit + single-ended bit
		commandout <<= 3    # we only need to send 5 bits here
		for i in range(5):
			if (commandout & 0x80):
				GPIO.output(self.mosi, True)
			else:
				GPIO.output(self.mosi, False)
			commandout <<= 1
			GPIO.output(self.clock, True)
			GPIO.output(self.clock, False)
	 
		adcout = 0
		# read in one empty bit, one null bit and 10 ADC bits
		for i in range(12):
			GPIO.output(self.clock, True)
			GPIO.output(self.clock, False)
			adcout <<= 1
			if (GPIO.input(self.miso)):
				adcout |= 0x1
	 
		GPIO.output(self.cs, True)
		
		adcout >>= 1       # first bit is 'null' so drop it
		return adcout

if __name__ == "__main__":

	GPIO.setmode(GPIO.BCM)
	mcp = Mcp3008(11,10,9,8)

	potentiometer_adc = 0;

	while 1:
		trim_pot = mcp.read(potentiometer_adc)
		print("pot: ", trim_pot)
		time.sleep(0.5)


	
