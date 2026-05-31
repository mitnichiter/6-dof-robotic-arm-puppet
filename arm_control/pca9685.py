import ustruct
import time

class PCA9685:
    def __init__(self, i2c, address=0x40):
        self.i2c = i2c
        self.address = address
        self.reset()

    def _write(self, address, value):
        self.i2c.writeto_mem(self.address, address, bytearray([value]))

    def _read(self, address):
        return self.i2c.readfrom_mem(self.address, address, 1)[0]

    def reset(self):
        self._write(0x00, 0x00) # Mode1

    def freq(self, freq=None):
        if freq is None:
            return int(25000000.0 / 4096 / (self._read(0xfe) - 0.5))
        prescale = int(25000000.0 / 4096.0 / freq - 0.5)
        old_mode = self._read(0x00)
        self._write(0x00, (old_mode & 0x7F) | 0x10) # sleep
        self._write(0xfe, prescale) # prescale
        self._write(0x00, old_mode) # wake
        time.sleep_us(5)
        self._write(0x00, old_mode | 0xa1) # autoincrement

    def pwm(self, index, on=None, off=None):
        if on is None or off is None:
            data = self.i2c.readfrom_mem(self.address, 0x06 + 4 * index, 4)
            return ustruct.unpack('<HH', data)
        data = ustruct.pack('<HH', on, off)
        self.i2c.writeto_mem(self.address, 0x06 + 4 * index, data)

    def duty(self, index, value=None, invert=False):
        if value is None:
            pwm = self.pwm(index)
            if pwm == (0, 4096):
                value = 0
            elif pwm == (4096, 0):
                value = 4095
            else:
                value = pwm[1]
            if invert:
                value = 4095 - value
            return value
        if not 0 <= value <= 4095:
            raise ValueError("Out of range")
        if invert:
            value = 4095 - value
        if value == 0:
            self.pwm(index, 0, 4096)
        elif value == 4095:
            self.pwm(index, 4096, 0)
        else:
            self.pwm(index, 0, value)

class Servos:
    def __init__(self, i2c, address=0x40, freq=50, min_us=600, max_us=2400, degrees=180):
        self.pca9685 = PCA9685(i2c, address)
        self.pca9685.freq(freq)
        self.period = 1000000 / freq
        self.min_duty = self._us2duty(min_us)
        self.max_duty = self._us2duty(max_us)
        self.degrees = degrees

    def _us2duty(self, value):
        return int(4095 * value / self.period)

    def position(self, index, degrees=None, us=None, duty=None):
        if degrees is not None:
            duty = int(self.min_duty + (self.max_duty - self.min_duty) * (degrees / self.degrees))
        elif us is not None:
            duty = self._us2duty(us)
        elif duty is not None:
            pass
        else:
            return self.pca9685.duty(index)
        self.pca9685.duty(index, duty)
