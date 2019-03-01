# Send measurement dat to Luftdaten API using HTTP posts
from __future__ import print_function

import requests
import syslog

class LuftDaten() :

    def __init__(self):
        self.sensorID = "raspi-" + self.get_serial()


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
                        "sensordatavalues": [{"value_type": key, "value": val} for key, val in values.items()],
                    },
                    headers={
                        "X-PIN":    str(pin),
                        "X-Sensor": self.sensorID,
                    }, timeout=10)

                print ("Status:", req)
                syslog.syslog(syslog.LOG_DEBUG, "Lufdaten post data status:" + str(req))
                return
            except:
                syslog.syslog(syslog.LOG_DEBUG, "Exception pushing data to Luftdaten")


# Main program - for testing purposes
if __name__ == "__main__":

    luft = LuftDaten()
    luft.send(10.0, 10.0)
