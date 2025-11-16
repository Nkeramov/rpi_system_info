# Raspberry Pi System Info

[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846.svg?logo=Raspberry-Pi)](https://www.raspberrypi.com/)
![Python](https://img.shields.io/badge/python-3.11-blue.svg)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![license](https://img.shields.io/badge/licence-MIT-green.svg)](https://opensource.org/licenses/MIT)


This project is a simple web server that displays system information about your Raspberry Pi.

<div align="center">
    <img src="title.png" width="75%">
</div>

The interface is divided into 4 tabs:
- 1️⃣  *General*: 
    - Board info (model, revision, manufacturer, OS name, host name, system time and uptime, internet connection status and public IP if connections is active)
    - CPU details (model, architecture, cores count, cores frequency, cores voltage, temperature, usage, cache sizes)
    - RAM details (size, total, used, free, cache, available)
- 2️⃣  *Networks*:
    - Ethernet adapter details (MAC and IP adresses, default gateway, network mask, broadcast IP adress)
    - Wi-Fi afapter details (MAC and IP adresses, default gateway, network mask, broadcast IP adress)
    - Available Wi-Fi networks (SSID, channel, rate, signal, bars, security). If the networkы list only shows the network the Raspberry Pi is connected to, you need to force a scan using the `sudo nmcli dev wifi rescan` command. This will be fixed in future versions.
    - Bluetooth details (MAC address)
- 3️⃣  *Storage*:
    - Disks usage details (file system, size, used, available, used%, mounted on).
    - Disks inodes details (file system, inodes, used, free, used%, mounted on).
    - ~~SD card details~~ (will be added in the future versions).
- 4️⃣  *Processes*: shows only running processes (user, PID, CPU%, MEM%, command, started on time)

Some information is parsed from the device's [revision code](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes) located in /proc/cpuinfo.

Information about disks and processes is presented in the form of tables. You can sort the tables by clicking on the column in the header.

The web server is based on Flask framework. By default the application will run on port 8080. It can be changed in env file. Gunicorn is used to launch.

## 🚀 Quick start

### Prerequisites
Clone repository:
```bash 
git clone https://github.com/Nkeramov/rpi_system_info.git
```
Switch to repo directory:
```bash 
cd rpi_system_info
```
### Traditional method with venv and pip
Create and activate virtual environment:
```bash 
python -m venv .venv 
source .venv/bin/activate       # Linux/Mac
# or
./venv/Scripts/activate         # Windows
```
Install dependencies and run:
```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8080 main:app
```
### Modern method with uv
Install dependencies and create virtual environment automatically:
```bash
uv sync
```
Run the project (virtual environment is handled automatically):
```bash
uv run gunicorn --bind 0.0.0.0:8080 main:app
```
Or with explicit activation:
```bash
source .venv/bin/activate       # After uv sync
gunicorn --bind 0.0.0.0:8080 main:app
```

Also you can use the launch script `run.sh`, making it executable first
```bash
chmod +x run.sh
```

## 🛠️  Configuration 

The configuration file is located in the `.env` file. You can copy the `env.example` to `.env` and make your edits.
```bash
cp env.example .env
```

## ⚙️  Adding to startup

You can set up automatic script launch at system startup.

Open the `/etc/rc.local` file in editor:
```bash
sudo nano /etc/rc.local
```
Add to the end of file this line:
```bash
/home/pi/rpi_system_info/run.sh &
```
Press Ctrl+O → Enter → Ctrl+X to save and exit.

## 🤝 Contributing

If you want to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push to your fork and create a pull request.

## 📝 License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## 📚 References 

- [Getting started](https://www.raspberrypi.com/documentation/computers/getting-started.html)
- [Raspberry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html)
- [Processors](https://www.raspberrypi.com/documentation/computers/processors.html)
- [Raspberry Pi hardware](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Raspberry Pi revision codes](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes)
- [How to Benchmark a Raspberry Pi Using Vcgencmd](https://www.tomshardware.com/how-to/raspberry-pi-benchmark-vcgencmd)
