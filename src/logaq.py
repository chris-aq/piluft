#!/usr/bin/python
# coding=utf-8
# "DATASHEET": https://cdn.sparkfun.com/assets/parts/1/2/2/7/5/Laser_Dust_Sensor_Control_Protocol_V1.3.pdf
# https://gist.github.com/kadamski/92653913a53baf9dd1a8
#
# Notes:
# To allow user to acces the tty port: sudo usermod -a -G dialout <user>

from __future__ import print_function
import serial, struct, sys, time, datetime, os
import csv
import numpy as np
import syslog
from luftdaten import LuftDaten


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

ser = serial.Serial(timeout=8, write_timeout=8)
ser.port = "/dev/ttyUSB0"
ser.baudrate = 9600

ser.open()
ser.flushInput()

byte, data = 0, ""

def dump(d, prefix=''):
    print(prefix + ' '.join(x.encode('hex') for x in d))

def construct_command(cmd, data=[]):
    assert len(data) <= 12
    data += [0,]*(12-len(data))
    checksum = (sum(data)+cmd-2)%256
    ret = "\xaa\xb4" + chr(cmd)
    ret += ''.join(chr(x) for x in data)
    ret += "\xff\xff" + chr(checksum) + "\xab"

    if DEBUG:
        dump(ret, '> ')
    return ret

def process_data(d):
    r = struct.unpack('<HHxxBB', d[2:])
    pm25 = r[0]/10.0
    pm10 = r[1]/10.0
    checksum = sum(ord(v) for v in d[2:8])%256
    return [pm25, pm10]
    syslog.syslog(syslog.LOG_DEBUG, "PM 2.5: {} μg/m^3  PM 10: {} μg/m^3 CRC={}".format(pm25, pm10, "OK" if (checksum==r[2] and r[3]==0xab) else "NOK"))
    #print("PM 2.5: {} μg/m^3  PM 10: {} μg/m^3 CRC={}".format(pm25, pm10, "OK" if (checksum==r[2] and r[3]==0xab) else "NOK"))

def process_version(d):
    r = struct.unpack('<BBBHBB', d[3:])
    checksum = sum(ord(v) for v in d[2:8])%256
    print("Y: {}, M: {}, D: {}, ID: {}, CRC={}".format(r[0], r[1], r[2], hex(r[3]), "OK" if (checksum==r[4] and r[5]==0xab) else "NOK"))

def read_response():
    byte = 0
    while byte != "\xaa":
        byte = ser.read(size=1)
        if len(byte) == 0 : return None

    d = ser.read(size=9)

    if DEBUG:
        dump(d, '< ')
    return byte + d

def reset_serial() :
    ser.reset_input_buffer()
    ser.reset_output_buffer()
    ser.close()
    ser.open()

def cmd_set_mode(mode=MODE_QUERY):
    ser.write(construct_command(CMD_MODE, [0x1, mode]))
    read_response()

def cmd_query_data():
    syslog.syslog(syslog.LOG_DEBUG, "Sending CMD_QUERY_DATA")
    ser.write(construct_command(CMD_QUERY_DATA))
    syslog.syslog(syslog.LOG_DEBUG, "Waiting for response")
    d = read_response()
    if d is None : return None
    syslog.syslog(syslog.LOG_DEBUG, "Response received")
    values = []
    if d[1] == "\xc0":
        values = process_data(d)
    return values

def cmd_set_sleep(sleep=1):
    mode = 0 if sleep else 1
    ser.write(construct_command(CMD_SLEEP, [0x1, mode]))
    read_response()

def cmd_set_working_period(period):
    ser.write(construct_command(CMD_WORKING_PERIOD, [0x1, period]))
    read_response()

def cmd_firmware_ver():
    ser.write(construct_command(CMD_FIRMWARE))
    d = read_response()
    process_version(d)

def cmd_set_id(id):
    id_h = (id>>8) % 256
    id_l = id % 256
    ser.write(construct_command(CMD_DEVICE_ID, [0]*10+[id_l, id_h]))
    read_response()

if __name__ == "__main__":

    luft = LuftDaten()

    while True:
        cmd_set_sleep(0)
        cmd_set_mode(1);
        time.sleep(2)

        # Values lists for pm value median calculation
        values_pm25 = []
        values_pm10 = []

        for t in range(NUM_READINGS):
            time.sleep(3)
            values = cmd_query_data();
            if values is not None and len(values) == 2 :
                values_pm25.append(values[0])
                values_pm10.append(values[1])
                syslog.syslog(syslog.LOG_DEBUG, "PM2.5: " + str(values[0]) + ", PM10: " + str(values[1]))
                print("PM2.5: ", values[0], ", PM10: ", values[1])
            else:
                syslog.syslog(syslog.LOG_DEBUG, "Reading failed - resetting serial device")
                print("Reading failed - resetting serial device")
                time.sleep(3)
                reset_serial()
                break


        # Set the SDS011 to sleep
        cmd_set_mode(0);
        cmd_set_sleep()
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
