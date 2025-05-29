# Raspberry Pi system info

[![license](https://img.shields.io/npm/l/pirev.svg?style=flat)](https://opensource.org/licenses/MIT)

This project is a simple web server that displays system information about your Raspberry Pi.

<div align="center">
    <img src="title.png">
</div>

The information includes generic board info, CPU details (model, architecture, number of cores, frequency, voltage, temperature, usage), RAM (total, used, free, cache, available), network interfaces (ip, mac), mounted disks and processes running in the system. 

Some information is parsed from the device's [revision code](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes) located in /proc/cpuinfo.

Information about disks and processes is presented in the form of tables. You can sort the tables by clicking on the column in the header.

The web server is based on Flask framework. By default the application will run on port 8080. It can be changed in env file.

Gunicorn is used to launch. Use run.sh to run project.
