#placeholder for Vishay VEML6070 UV-A light sensor
#this light sensor outputs UV-A sensor readings via the I2C bus
#There's existing code for Arduino using this, so it shouldn't be hard to cross-compile it to python
#datasheet located here https://www.vishay.com/docs/84310/designingveml6070.pdf

#python code from Raspberry Pi 2/3 from https://github.com/cmur2/python-veml6070
#The MIT License (MIT)
#
#Copyright (c) 2016 Christian Nicolai
#
#Permission is hereby granted, free of charge, to any person obtaining a copy
#of this software and associated documentation files (the "Software"), to deal
#in the Software without restriction, including without limitation the rights
#to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
#copies of the Software, and to permit persons to whom the Software is
#furnished to do so, subject to the following conditions:
#
#The above copyright notice and this permission notice shall be included in all
#copies or substantial portions of the Software.

#THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
#IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
#FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
#AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
#LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
#OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
#SOFTWARE.
import time

import smbus # pylint: disable=import-error

ADDR_L = 0x38 # 7bit address of the VEML6070 (write, read)
ADDR_H = 0x39 # 7bit address of the VEML6070 (read)

RSET_240K = 240000
RSET_270K = 270000
RSET_300K = 300000
RSET_600K = 600000

SHUTDOWN_DISABLE = 0x00
SHUTDOWN_ENABLE = 0x01

INTEGRATIONTIME_1_2T = 0x00
INTEGRATIONTIME_1T = 0x01
INTEGRATIONTIME_2T = 0x02
INTEGRATIONTIME_4T = 0x03

class Veml6070(object):

    def __init__(self, i2c_bus=1, sensor_address=ADDR_L, rset=RSET_270K, integration_time=INTEGRATIONTIME_1T):
        self.bus = smbus.SMBus(i2c_bus)
        self.sendor_address = sensor_address
        self.rset = rset
        self.shutdown = SHUTDOWN_DISABLE # before set_integration_time()
        self.set_integration_time(integration_time)
        self.disable()

    def set_integration_time(self, integration_time):
        self.integration_time = integration_time
        self.bus.write_byte(self.sendor_address, self.get_command_byte())
        # constant offset determined experimentally to allow sensor to readjust
        time.sleep(0.2)

    def get_integration_time(self):
        return self.integration_time

    def enable(self):
        self.shutdown = SHUTDOWN_DISABLE
        self.bus.write_byte(self.sendor_address, self.get_command_byte())

    def disable(self):
        self.shutdown = SHUTDOWN_ENABLE
        self.bus.write_byte(self.sendor_address, self.get_command_byte())

    def get_uva_light_intensity_raw(self):
        self.enable()
        # wait two times the refresh time to allow completion of a previous cycle with old settings (worst case)
        time.sleep(self.get_refresh_time()*2)
        msb = self.bus.read_byte(self.sendor_address+(ADDR_H-ADDR_L))
        lsb = self.bus.read_byte(self.sendor_address)
        self.disable()
        return (msb << 8) | lsb

    def get_uva_light_intensity(self):
        uv = self.get_uva_light_intensity_raw()
        return uv * self.get_uva_light_sensitivity()

    def get_command_byte(self):
        """
        assembles the command byte for the current state
        """
        cmd = (self.shutdown & 0x01) << 0 # SD
        cmd = (self.integration_time & 0x03) << 2 # IT
        cmd = ((cmd | 0x02) & 0x3F) # reserved bits
        return cmd

    def get_refresh_time(self):
        """
        returns time needed to perform a complete measurement using current settings (in s)
        """
        case_refresh_rset = {
            RSET_240K: 0.1,
            RSET_270K: 0.1125,
            RSET_300K: 0.125,
            RSET_600K: 0.25
        }
        case_refresh_it = {
            INTEGRATIONTIME_1_2T: 0.5,
            INTEGRATIONTIME_1T: 1,
            INTEGRATIONTIME_2T: 2,
            INTEGRATIONTIME_4T: 4
        }
        return case_refresh_rset[self.rset] * case_refresh_it[self.integration_time]

    def get_uva_light_sensitivity(self):
        """
        returns UVA light sensitivity in W/(m*m)/step
        """
        case_sens_rset = {
            RSET_240K: 0.05,
            RSET_270K: 0.05625,
            RSET_300K: 0.0625,
            RSET_600K: 0.125
        }
        case_sens_it = {
            INTEGRATIONTIME_1_2T: 0.5,
            INTEGRATIONTIME_1T: 1,
            INTEGRATIONTIME_2T: 2,
            INTEGRATIONTIME_4T: 4
        }
        return case_sens_rset[self.rset] / case_sens_it[self.integration_time]
