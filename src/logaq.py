#!/usr/bin/python
# coding=utf-8
# "DATASHEET": https://cdn.sparkfun.com/assets/parts/1/2/2/7/5/Laser_Dust_Sensor_Control_Protocol_V1.3.pdf
#
# Notes:
# To allow user to access the tty port: sudo usermod -a -G dialout <user>


import serial, struct, sys, time, datetime, os
import csv
import numpy as np
import syslog
import argparse
import requests

AIR_QUALITY_FILENAME = os.path.expanduser("~/airquality.csv")
PERIOD = 300         # Seconds
NUM_READINGS = 10

DEBUG = 0
CMD_MODE = 2
CMD_QUERY_DATA = 4
CMD_DEVICE_ID = 5
CMD_SLEEP = 6
CMD_FIRMWARE = 7
CMD_WORKING_PERIOD = 8
MODE_ACTIVE = 0
MODE_QUERY = 1


""" Send measurement data to Luftdaten API using HTTP posts
"""
class LuftDaten() :

    def __init__(self, sensorID=None):
        if sensorID is None :
            self.sensorID = "raspi-" + self.get_serial()
        else:
            self.sensorID = sensorID
        print("Sensor ID for this system for Luftdaten is: " + self.sensorID)


    # Get the serial number from cpuinfo
    def get_serial(self):
        with open('/proc/cpuinfo','r') as f:
            for line in f:
                if line[0:6]=='Serial':
                    return(line[10:26])
        return "0000000000000000"


    # Send data to Luftdaten API as HTTP POST
    def send(self, pm10_value, pm25_value):

        url = 'https://api.luftdaten.info/v1/push-sensor-data/'
        pin = 1
        values = {"P1": round(pm10_value,2), "P2": round(pm25_value,2),}

        print("Pushing data for Luftdaten SDS011 sensor " + self.sensorID + ": " + str(values))
        syslog.syslog(syslog.LOG_DEBUG, "Pushing data for Luftdaten SDS011 sensor " + self.sensorID + ": " + str(values))

        # Try pushing the data up to 4 times
        for i in range(4) :
            try:
                req = requests.post(url,
                    json={
                        "software_version": "python-lufty 0.1",
                        "sensordatavalues": [{"value_type": key, "value": val} for key, val in list(values.items())],
                    },
                    headers={
                        "X-PIN":    str(pin),
                        "X-Sensor": self.sensorID,
                    }, timeout=10)

                print ("Status:", req)
                syslog.syslog(syslog.LOG_DEBUG, "Lufdaten post data status:" + str(req))
                return
            except Exception as e:
                syslog.syslog(syslog.LOG_DEBUG, "Exception pushing data to Luftdaten: " + str(e))
                time.sleep(2)

class SDS011(object):
    """Provides method to read from a SDS011 air particlate density sensor
    using UART.
    """

    HEAD = b'\xaa'
    TAIL = b'\xab'
    CMD_ID = b'\xb4'

    # The sent command is a read or a write
    READ = b"\x00"
    WRITE = b"\x01"

    REPORT_MODE_CMD = b"\x02"
    ACTIVE = b"\x00"
    PASSIVE = b"\x01"

    QUERY_CMD = b"\x04"

    # The sleep command ID
    SLEEP_CMD = b"\x06"
    # Sleep and work byte
    SLEEP = b"\x00"
    WORK = b"\x01"

    # The work period command ID
    WORK_PERIOD_CMD = b'\x08'

    def __init__(self, serial_port, baudrate=9600, timeout=2,
                 use_query_mode=True):
        """Initialise and open serial port.
        """
        self.ser = serial.Serial(port=serial_port,
                                 baudrate=baudrate,
                                 timeout=timeout)
        self.ser.flush()
        self.set_report_mode(active=not use_query_mode)

    def _execute(self, cmd_bytes):
        """Writes a byte sequence to the serial.
        """
        self.ser.write(cmd_bytes)

    def _get_reply(self):
        """Read reply from device."""
        raw = self.ser.read(size=10)
        data = raw[2:8]
        if len(data) == 0:
            return None
        if (sum(d for d in data) & 255) != raw[8]:
            return None  #TODO: also check cmd id
        return raw

    def cmd_begin(self):
        """Get command header and command ID bytes.
        @rtype: list
        """
        return self.HEAD + self.CMD_ID

    def set_report_mode(self, read=False, active=False):
        """Get sleep command. Does not contain checksum and tail.
        @rtype: list
        """
        cmd = self.cmd_begin()
        cmd += (self.REPORT_MODE_CMD
                + (self.READ if read else self.WRITE)
                + (self.ACTIVE if active else self.PASSIVE)
                + b"\x00" * 10)
        cmd = self._finish_cmd(cmd)
        self._execute(cmd)
        self._get_reply()

    def query(self):
        """Query the device and read the data.

        @return: Air particulate density in micrograms per cubic meter.
        @rtype: tuple(float, float) -> (PM2.5, PM10)
        """
        cmd = self.cmd_begin()
        cmd += (self.QUERY_CMD
                + b"\x00" * 12)
        cmd = self._finish_cmd(cmd)
        self._execute(cmd)

        raw = self._get_reply()
        if raw is None:
            return None  #TODO:
        data = struct.unpack('<HH', raw[2:6])
        pm25 = data[0] / 10.0
        pm10 = data[1] / 10.0
        return (pm25, pm10)

    def sleep(self, read=False, sleep=True):
        """Sleep/Wake up the sensor.

        @param sleep: Whether the device should sleep or work.
        @type sleep: bool
        """
        cmd = self.cmd_begin()
        cmd += (self.SLEEP_CMD
                + (self.READ if read else self.WRITE)
                + (self.SLEEP if sleep else self.WORK)
                + b"\x00" * 10)
        cmd = self._finish_cmd(cmd)
        self._execute(cmd)
        self._get_reply()

    def set_work_period(self, read=False, work_time=0):
        """Get work period command. Does not contain checksum and tail.
        @rtype: list
        """
        assert work_time >= 0 and work_time <= 30
        cmd = self.cmd_begin()
        cmd += (self.WORK_PERIOD_CMD
                + (self.READ if read else self.WRITE)
                + bytes([work_time])
                + b"\x00" * 10)
        cmd = self._finish_cmd(cmd)
        self._execute(cmd)
        self._get_reply()

    def _finish_cmd(self, cmd, id1=b"\xff", id2=b"\xff"):
        """Add device ID, checksum and tail bytes.
        @rtype: list
        """
        cmd += id1 + id2
        checksum = sum(d for d in cmd[2:]) % 256
        cmd += bytes([checksum]) + self.TAIL
        return cmd

    def _process_frame(self, data):
        """Process a SDS011 data frame.

        Byte positions:
            0 - Header
            1 - Command No.
            2,3 - PM2.5 low/high byte
            4,5 - PM10 low/high
            6,7 - ID bytes
            8 - Checksum - sum of bytes 2-7
            9 - Tail
        """
        raw = struct.unpack('<HHxxBBB', data[2:])
        checksum = sum(v for v in data[2:8]) % 256
        if checksum != data[8]:
            return None
        pm25 = raw[0] / 10.0
        pm10 = raw[1] / 10.0
        return (pm25, pm10)

    def read(self):
        """Read sensor data.

        @return: PM2.5 and PM10 concetration in micrograms per cude meter.
        @rtype: tuple(float, float) - first is PM2.5.
        """
        byte = 0
        while byte != self.HEAD:
            byte = self.ser.read(size=1)
            d = self.ser.read(size=10)
            if d[0:1] == b"\xc0":
                data = self._process_frame(byte + d)
                return data

    def reset_serial(self) :
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()
        self.ser.close()
        self.ser.open()

            

""" Class to control and take readings from the SDS011 air quality sensor.
"""


# Main program
if __name__ == "__main__":

    ap = argparse.ArgumentParser()
    ap.add_argument('tty_device', nargs='?', default="/dev/ttyUSB0", help="The name of the tty device e.g. /dev/ttyUSB0")
    ap.add_argument("-i", "--id", type=str, default=None, help="Lufdaten ID e.g raspi-0000000012345678")

    args = vars(ap.parse_args())
    tty_device = args["tty_device"]
    lufdaten_id = args["id"]
    print("Using serial device: " + tty_device)

    sds011 = SDS011(serial_port=tty_device)
    sds011 = SDS011("/dev/ttyUSB0", use_query_mode=True)


    luft = LuftDaten(sensorID=lufdaten_id)

    while True:
        sds011.sleep(sleep=False)
        # self.cmd_set_mode(1);
        time.sleep(2)

        # Values lists for pm value median calculation
        values_pm25 = []
        values_pm10 = []

        for t in range(NUM_READINGS):
            time.sleep(3)
            values = sds011.query()
            if values is not None and len(values) == 2 :
                values_pm25.append(values[0])
                values_pm10.append(values[1])
                syslog.syslog(syslog.LOG_DEBUG, "PM2.5: " + str(values[0]) + ", PM10: " + str(values[1]))
                print("PM2.5: ", values[0], ", PM10: ", values[1])
            else:
                syslog.syslog(syslog.LOG_DEBUG, "Reading failed - resetting serial device")
                print("Reading failed - resetting serial device")
                time.sleep(3)
                sds011.reset_serial()
                break


        # Set the SDS011 to sleep
        sds011.sleep()
        syslog.syslog(syslog.LOG_DEBUG, "SDS011 sensor set to sleep")

        # Log the values and send to Luftdaten
        if len(values_pm25) == NUM_READINGS and len(values_pm10) == NUM_READINGS :
            median_pm25 = np.median(values_pm25)
            median_pm10 = np.median(values_pm10)

            # Log the data to csv file
            with open(AIR_QUALITY_FILENAME, "a+") as f:
                writer = csv.writer(f, delimiter=",")
                writer.writerow([datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S"), round(median_pm25, 2), round(median_pm10, 2)])
                f.flush()

            # Send the data to Luftdaten - PM10 and PM25
            luft.send(median_pm10, median_pm25)


        # Sleep until the next measurement interval has expired
        sleep_period = (PERIOD - time.time()) % PERIOD
        syslog.syslog(syslog.LOG_DEBUG, "Going to sleep for " + str(sleep_period) + "s")
        print ("Going to sleep for", sleep_period, "s")
        time.sleep(sleep_period)
        print ("Waking up")

