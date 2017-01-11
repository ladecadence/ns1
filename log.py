import datetime
from enum import Enum

class LogType(Enum):
	DATA = 0
	INFO = 1
	WARN = 2
	ERR = 3


class Log:
	def __init__(self, filename):
		self.filename = filename

	def reset(self):
		# reset file
		f = open(self.filename, "w")
		f.close()
	
	def log(self, t, msg):
		f = open(self.filename, "a")
		
		# write msg type
		if t == LogType.DATA:
			f.write("DATA\t")
		elif t == LogType.INFO:
			f.write("INFO\t")
		elif t == LogType.WARN:
			f.write("WARN\t")
		elif t == LogType.ERR:
			f.write("ERR\t")
		else:
			pass

		# write date
		f.write(datetime.datetime.now().isoformat()+"\t")
		f.write(msg)
		f.write("\n")

		# close it
		f.close()


