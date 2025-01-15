# Raspberry Pi system info

This project is a simple web server that displays system information about your Raspberry Pi.

The information includes data about the board model, hostname, OS details, CPU (type, architecture, revision, serial number, numer of cores, frequency, voltage, temperature, usage), RAM (total, used, free, cache, available), network interfaces (ip, mac), mounted disks and processes running in the system. 

The web server is based on Flask. The application will run on port 8080. It can be specified to run on any port in env file.

Gunicorn is used to launch. Use run.sh to run project.
