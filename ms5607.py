import smbus
import time

# MS5607 I2C commands
MS5607_CMD_RESET    = 0x1E    # reset
MS5607_CMD_ADC_READ = 0x00    # read sequence
MS5607_CMD_ADC_CONV = 0x40    # start conversion
MS5607_CMD_ADC_D1   = 0x00    # read ADC 1
MS5607_CMD_ADC_D2   = 0x10    # read ADC 2
MS5607_CMD_ADC_256  = 0x00    # ADC oversampling ratio to 256
MS5607_CMD_ADC_512  = 0x02    # ADC oversampling ratio to 512
MS5607_CMD_ADC_1024 = 0x04    # ADC oversampling ratio to 1024
MS5607_CMD_ADC_2048 = 0x06    # ADC oversampling ratio to 2048
MS5607_CMD_ADC_4096 = 0x08    # ADC oversampling ratio to 4096
MS5607_CMD_PROM_RD  = 0xA0    # readout of PROM registers


class MS5607:
    def __init__(self, bus=0, addr=0x77):
        self.bus = bus
        self.addr = addr
        self.C = [0,0,0,0,0,0,0]

    def read_prom(self):
        bus = smbus.SMBus(self.bus)
        bus.write_byte_data(self.addr, 0, MS5607_CMD_RESET)

        time.sleep(0.03)
        
        for i in range(1,7):
            self.C[i] = 0x0000
            (data1, data0) = bus.read_i2c_block_data(self.addr, MS5607_CMD_PROM_RD+(2*i), 2)
            self.C[i] = data1 << 8
            self.C[i] = self.C[i] + data0

        bus.close()

    def read_adc(self, cmd):
        value = 0

        bus = smbus.SMBus(self.bus)
        bus.write_byte_data(self.addr, MS5607_CMD_ADC_CONV+cmd, 0)

        if (cmd & 0x0f) == MS5607_CMD_ADC_256 :
            time.sleep(0.0009)
        elif (cmd & 0x0f) == MS5607_CMD_ADC_512:
            time.sleep(0.003)
        elif (cmd & 0x0f) == MS5607_CMD_ADC_1024:
            time.sleep(0.004)
        elif (cmd & 0x0f) == MS5607_CMD_ADC_2048:
            time.sleep(0.006)
        elif (cmd & 0x0f) == MS5607_CMD_ADC_4096:
            time.sleep(0.01)

        (data2, data1, data0) = bus.read_i2c_block_data(self.addr, MS5607_CMD_ADC_READ, 3)

        value = (data2 << 16) + (data1 << 8) + data0
        
        bus.close()

        return value

    def update(self):
        D2=self.read_adc(MS5607_CMD_ADC_D2+MS5607_CMD_ADC_4096)
        D1=self.read_adc(MS5607_CMD_ADC_D1+MS5607_CMD_ADC_4096)
        
        # calculate 1st order pressure and temperature (MS5607 1st order algorithm)
        dT=D2-self.C[5]*(2**8)
        OFF=self.C[2]*(2**17)+dT*self.C[4]/(2**6)
        SENS=self.C[1]*(2**16)+dT*self.C[3]/(2**7)
        self.TEMP=(2000+(dT*self.C[6])/(2**23))
        self.P=(((D1*SENS)/(2**21)-OFF)/(2**15))

        T2 = 0
        OFF2 = 0
        SENS2 = 0

        # perform higher order corrections
        if self.TEMP<2000 :
            T2=dT*dT/(2**31)
            OFF2=61*(self.TEMP-2000)*(self.TEMP-2000)/(2**4)
            SENS2=2*(self.TEMP-2000)*(self.TEMP-2000)
            if self.TEMP<-1500:
                OFF2=OFF2+(15*(self.TEMP+1500)*(self.TEMP+1500))
                SENS2=SENS2+(8*(self.TEMP+1500)*(self.TEMP+1500))

        self.TEMP = self.TEMP-T2
        OFF = OFF - OFF2
        SENS = SENS - SENS2

        self.P=(((D1*SENS)/(2**21)-OFF)/(2**15))

    def get_temp(self):
        # degrees C
        return self.TEMP/100

    def get_pres(self):
        # mBar
        return self.P/100


if __name__ == "__main__":
    sens = MS5607(1, 0x77)
    sens.read_prom()
    sens.update()

    print("Temperature: " + "{0:.2f}".format(sens.get_temp()) + " ºC")
    print("Pressure: " + "{0:.2f}".format(sens.get_pres()) + " mBar")


