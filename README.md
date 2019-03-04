# Raspberry Pi Air Quality Measurements for Luftdaten

This provides basic Python software running on a Raspberry Pi computer to read data from a Nova SDS011 Air Quality Sensor, log the data to a .csv file, and send the data to the Luftdaten site.
The sensor is woken every 5 minutes and readings of PM2.5 and PM10 are taken and logged. This mode of operation should extend the lifetime of the sensor to over 3 years as it is only awake for around 10% of the time.

Below are basic instructions on how to set the Raspberry Pi up to read data from the air quality sensor.
Details of how to physically set up the sensor in a waterproof case are provided on the Luftdaten website.

## Requirements
This guide assumes basic knowledge of electronics, the Unix environment, and some experience with the Raspberry Pi platform itself.

### Hardware

#### RPi control box
A Raspberry Pi Zero, 1, 2 or 3B, with one available USB port. Power supply. 8GB or 16GB SD Card.
Recommend that the latest version of Raspbian is installed. At the time of writing, this is Raspbian Stretch.

A Wifi connection to the internet (or wired ethernet for the Pi3B) is required to log the data to the Luftdaten server.

#### Nova SDS011 Air Quality Sensor
This is connected to the USB (or micro-USB for Pi Zero) port of the Raspberry Pi.


### Software

#### Additional Software Modules
The following additional modules are required to run the software.
These can be installed with the command:
```
sudo apt install python-requests python-serial python-numpy python-setuptools python-pip git libusb-dev
```

#### Serial Port
To allow the software to access the serial port connected to the air quality sensor, the user must be allowed access to the serial device.
This can be done with the command:
```
sudo usermod -a -G dialout <username>
```

... where \<username\> is the current username. e.g. pi


#### Luftdaten API
To send data to the Luftdaten API, the software uses the Serial ID of the Raspberry Pi from the file /proc/cpuinfo prefixed with raspi-. For example:
raspi-0000000123456789

When the software is run, it will print the ID to be used for Luftdaten. You will then need to register the sensor with Luftdaten using this ID on their website.
If you have not registered with Luftdaten, the software will still run but will just log the date/time, PM2.5 and PM10 data to the file ~/airquality.csv .

## Running the software

To start the software run the command:
```
logaq.py
```

The serial port connected to the sensor is assumed by the software to be /dev/ttyUSB0 . If this is not the case, pass the device name in the command line option e.g.
```
logaq.py /dev/ttyUSB1
```

To make the software run automatically on every boot, add the command to crontab using the command:
```
crontab -e
```

Then add the following line at the end of the crontab:
```
@reboot sleep 60 && <path_to_piluft_source>/logaq.py
```

... where \<path_to_piluft_source\> is the directory to the piluft software is installed from github e.g. /home/pi/piluft/src .

