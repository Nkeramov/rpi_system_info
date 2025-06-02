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

## Prerequisites

Install the requirements. To keep things simple, we will use the Python virtual environment.

```bash
        python -m venv .venv
        source .venv/bin/activate           # for linux and mac
        ./env/Scripts/activate              # for windows
        pip install -r requirements.txt
```

Make run.sh executable and use it to run project.

```bash
        chmod +x run.sh
        ./run.sh
```

## Configuration

The configuration file is located in the `.env` file. You can copy the `env.example` to `.env` and make your edits.

```bash
        cp env.example .env
```

## Contributing

We welcome contributions! If you want to contribute, please follow these steps:

1. Fork the repository.
2. Create a new branch for your feature or bug fix.
3. Make your changes and commit them.
4. Push to your fork and create a pull request.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Ref

- [Raspberry Pi hardware](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html)
- [Raspberry Pi revision codes](https://www.raspberrypi.com/documentation/computers/raspberry-pi.html#raspberry-pi-revision-codes)
- [Rasperry Pi OS](https://www.raspberrypi.com/documentation/computers/os.html)
- [How to Benchmark a Raspberry Pi Using Vcgencmd](https://www.tomshardware.com/how-to/raspberry-pi-benchmark-vcgencmd)
