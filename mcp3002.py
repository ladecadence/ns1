import spidev
import time

class Mcp3002:
    def __init__(self, cs=1):
        self.cs = cs
        self.spi = spidev.SpiDev()
        self.spi.open(0,self.cs)
        self.spi.max_speed_hz = 488000
        self.spi.close()
    
    def read(self, adc_number):
        if ((adc_number > 1) or (adc_number < 0)):
            return -1
        
        # Start bit, single channel read
        command = 0b11010000
        command |= adc_number << 5
        
        self.spi.open(0,self.cs)
        resp = self.spi.xfer2([command, 0x0, 0x0])
        self.spi.close()

        result = (resp[0] & 0x01) << 9
        result |= (resp[1] & 0xFF) << 1
        result |= (resp[2] & 0x80) >> 7
        return result & 0x3FF


if __name__ == "__main__":

    mcp = Mcp3002(1)

    potentiometer_adc = 1;

    while 1:
        trim_pot = mcp.read(potentiometer_adc)
        print("pot: ", trim_pot)
        time.sleep(0.5)


    
