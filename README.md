# Raspberry Pi System Info

[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846.svg?logo=Raspberry-Pi)](https://www.raspberrypi.com/)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![license](https://img.shields.io/badge/licence-MIT-green.svg)](https://opensource.org/licenses/MIT)


This project is a simple web server that displays system information about your Raspberry Pi.

<div align="center">
    <img src="title.png">
</div>

The information includes generic board info, CPU details (model, architecture, number of cores, frequency, voltage, temperature, usage), RAM (total, used, free, cache, available), network interfaces (ip, mac), mounted disks and processes running in the system. 

Some information is parsed from the device's [revision code](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes) located in /proc/cpuinfo.

Information about disks and processes is presented in the form of tables. You can sort the tables by clicking on the column in the header.

The web server is based on Flask framework. By default the application will run on port 8080. It can be changed in env file.

Gunicorn is used to launch.

## Setting up and running the project
Clone repository:
```bash 
git clone https://github.com/Nkeramov/raspberry_pi_system_info.git
```
Switch to repo directory
```bash 
cd raspberry_pi_system_info
```
Сreate new virtual environment:
```bash 
python -m venv .venv 
```
Activate the virtual environment with the command:
```bash 
source .venv/bin/activate
```
Install dependencies from the requirements file:
```bash
pip install -r requirements.txt
```
Run with command:
```bash
gunicorn --bind 0.0.0.0:8080 main:app
```
Or use a launch script `run.sh`, making it executable first
```bash
chmod +x run.sh
```

## Configuration

The configuration file is located in the `.env` file. You can copy the `env.example` to `.env` and make your edits.
```bash
cp env.example .env
```

## Adding to startup

You can set up automatic script launch at system startup.

Open the /etc/rc.local file in editor:
```bash
sudo nano /etc/rc.local
```
Add to the end of file this line:
```bash
/home/pi/raspberry_pi_system_info/run.sh &
```
Press Ctrl+O → Enter → Ctrl+X to save and exit.

## Contributing

If you want to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push to your fork and create a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Ref

- [Getting started](https://www.raspberrypi.com/documentation/computers/getting-started.html)
- [Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html)
- [Processors](https://www.raspberrypi.com/documentation/computers/processors.html)
- [Raspberry Pi hardware](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Raspberry Pi revision codes](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes)
- [How to Benchmark a Raspberry Pi Using Vcgencmd](https://www.tomshardware.com/how-to/raspberry-pi-benchmark-vcgencmd)
