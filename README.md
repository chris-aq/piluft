# Raspberry Pi Air Quality Measurements for Luftdaten

This provides basic Python software to read data from an SDS011 Air Quality Sensor, log the data to a .csv file, and send the data to the Luftdaten site.
Below are basic instructions on how to set the Raspberry Pi up to read data from the air quality sensor.

Details of how to physically set up the sensor are provided on the Luftdaten website.

## Requirements
This guide assumes basic knowledge of electronics, the Unix environment, and some experience with the Raspberry Pi platform itself.

### Hardware

#### RPi control box
A Raspberry Pi Zero or Raspberry Pi 3B with one available USB port. Recommend the latest version of Raspbian is installed.
At the time of writing, this is Raspbian Stretch.

A Wifi connection to the internet (or wired ethernet for the Pi3B)

#### SDS011 Air Quality Sensor
This is connected to the USB (or micro-USB for Pi Zero) port of the Raspberry Pi.


### Software

#### Additional Modules
The following additional modules are required to run the software.
These can be installed with the command:
```
sudo apt install python-requests python-serial python-numpy python-setuptools python-pip git libusb-dev
```

#### Serial Port
To allow the software to access the serial port connected to the air quality sensor, the user must be allowed access to the port.
This can be done with the command:
```
sudo usermod -a -G dialout <username>
```

... where \<username\> is the current username. e.g. pi


#### Luftdaten API
To send data to the Luftdaten API, the software uses the Serial ID of the Raspberry Pi from the file /proc/cpuinfo prefixed with raspi-. For example:
raspi-0000000164ad5f87

When the software is run, it will print the ID to be used for Luftdaten. You will then need to register the sensor with Luftdaten on their website.
If you have not registered with Luftdaten, the software will still run and log the date/time, PM2.5 and PM10 data in the file ~/airquality.csv .

## Running the software

To start the software run the command:
```
logaq.py
```

The serial port connected to the sensor is assumed by the software to be /dev/ttyUSB0 . If this is not the case, pass the device name in the command line option e.g.
```
logaq.py /dev/ttyUSB1
```

To make the software run automatically on every boot, add the command to crontab using the command :
```
crontab -e
```

Then add the following line at the end of the crontab:
```
@reboot sleep 60 && <path_to_piluft_source>/logaq.py
```

... where \<path_to_piluft_source\> is the directory to the piluft software is installed from github e.g. /home/pi/piluft/src .

