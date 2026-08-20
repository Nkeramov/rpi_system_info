# RPi System Info

[![Raspberry Pi](https://img.shields.io/badge/Raspberry%20Pi-A22846.svg?logo=Raspberry-Pi)](https://www.raspberrypi.com/)
[![Flask](https://img.shields.io/badge/Flask-web%20app-000000.svg?logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
![Python](https://img.shields.io/badge/python-3.11%2B-blue.svg)
[![Checked with mypy](http://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
[![license](https://img.shields.io/badge/licence-MIT-green.svg)](https://opensource.org/licenses/MIT)


This project is a simple web server that displays system information about your Raspberry Pi.

<div align="center">
    <img src="title.png" width="75%">
</div>

The interface is divided into 5 tabs:
- 1️⃣  *General*: 
    - Board Info: host name, operating system, system time and uptime, model, revision, manufacturer, serial number. 
    - Key Metrics: CPU metrics (usage, temperature, core frequency), RAM metrics (total, available), IP addresses of network interfaces eth0 and wlan0, internet connection status and public IP (if connection is active).
- 2️⃣  *Hardware*:
    - CPU Info: model, architecture, cores count, cores frequency (current, min, max), cores voltage, temperature, usage, cache sizes, overvoltage allowed, OTP programming allowed, OTP reading allowed).
    - RAM Info: capacity information and utilization (size, total, used, free, cache, available).
    - GPU Info: memory size (from RAM), status for for MPG2, WVC1, MPG4, MJPG, WMV9 codecs.
- 3️⃣  *Networks*:
    - Ethernet Adapter Info (for eth0 interface): MAC and IP adresses, default gateway, network mask, broadcast IP adress.
    - Wi-Fi Adapter Info (for wlan0 interface): MAC and IP adresses, default gateway, network mask, broadcast IP adress, Wi-Fi network name (if connected).
    - Available Wi-Fi Networks: SSID, channel, rate, signal, bars, security). If the networks list only shows the network the Raspberry Pi is connected to, you need to force a scan using the `sudo nmcli dev wifi rescan` command. This will be fixed in future versions.
    - Bluetooth Adapter Info (for hci0 interface): MAC address, status, name and adapter manufacturer.
- 4️⃣  *Storage*:
    - SD Card Info: name, device, serial number, manufacturer id and name (if it was possible to determine), registers info (CID, CSD, DSR, SCR, OCR), logical and physical block sizes.
    - Disks Usage Info: disks space information and utilization (file system, size, used, available, used percent, mounted on).
    - Disks Inodes Info: disks inodes utilization (file system, inodes, used, free, used percent, mounted on).
- 5️⃣  *Processes*:
    - Running Processes Info: user, PID, CPU and MEM percent, command, start time.
    - Tmux Sessions Info: session name, number of windows in the session, create time.

Some information is parsed from the device's [revision code](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes) located in /proc/cpuinfo.

Some information is presented in the form of tables (Wi-Fi networks, disks, running processes, tmux sesions). You can sort the tables by clicking on the column in the header.

The web server is based on Flask framework. Gunicorn is used to launch. By default the application will run on port 8080. Tab contents are dynamically loaded when a tab is activated. Tab contents are cached, with a default cache time of 30 seconds. Both the port and page caching time can be changed in the environment file.


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
source .venv/bin/activate
```
Install dependencies and run:
```bash
pip install -r requirements.txt
gunicorn --bind 0.0.0.0:8080 main:app
```
### Modern method with uv
Install dependencies and create virtual environment (.venv) automatically:
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

## Requirements

- Python 3.11+
- Works on all Raspberry Pi models running Raspberry Pi OS / Raspbian

## Color Coding

Thresholds for CPU usage and temperature, as well as memory usage:


| Color  | Meaning         | CPU / RAM | Temperature |
|--------|-----------------|-----------|-------------|
| 🟢 Green  | Normal          | < 65%     | < 55°C      |
| 🟡 Yellow | Warning         | 65–85%    | 55–70°C     |
| 🔴 Red    | Critical        | > 85%     | > 70°C      |


The table shows my settings, you can specify your desired ones in the env file.

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
- [RPI vcgencmd usage](https://elinux.org/RPI_vcgencmd_usage)
- [RPi Hub](https://elinux.org/RPi_Hub)
