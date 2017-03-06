# ASHAB.space 2017

# DS18B20 Temperature sensor class
# Uses linux sysfs so iy is just a a matter of
# opening a file in the /sys directory
# 1-Wire bus kernel module has to be enabled
class Ds18b20:
	def __init__(self, address):
        # select file based on sesnsor address
		self.sysfile="/sys/bus/w1/devices/"+address+"/w1_slave"

    # Tries to open the file and read the temperature value
    # if fails returns 0
	def read(self):
		try:
			f = open(self.sysfile)
			text = f.read()
			f.close()
		
			data = text.split("\n")[1].split(" ")[9]
			temp = float(data[2:])
			temp = temp/1000

			return temp
		except: 
			return 0


