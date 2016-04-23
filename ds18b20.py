

class Ds18b20:
	def __init__(self, address):
		self.sysfile="/sys/bus/w1/devices/"+address+"/w1_slave"
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


