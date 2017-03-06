# ASHAB NSX

Tracking and telemetry code for the ASHAB Payloads.

Transmits position/telemetry using digital packets and images using SSDV.
Runs on Raspberry Pi with raspbian, python, ssdv, imagemagick and PyRF95.
(https://github.com/ladecadence/pyRF95)

Designed to run on a raspberry pi zero with the stratozero board:
http://wiki.ashab.space/doku.php?id=stratozero

See: http://wiki.ashab.space/doku.php?id=nearspacetwo (Spanish)

## Modules:

* ashabgps.py : GPS control and decoding
* ds18b20.py : DS18B20 temperature sensors
* image.py : Image capture and SSDV generation
* led.py : Status LED methods
* log.py : Logging system
* mcp3002.py : SPI MCP3002 analog to digital converter
* ms5607.py : i2c barometer
* nsx.py : Main mission code
* run_ashab.sh : Init script





