# power-tests
This repository contains supplementary information about the investigation of performance of the SX126x power amplifier, also discussed in https://github.com/jgromes/RadioLib/issues/1628.

Software in this repository was run on a Raspberry Pi with attached [RadioHAT](https://github.com/radiolib-org/RadioHAT), interfacing with the SX126x under test. The HAT also provided the DC power measurements via its onboard INA219. The RF power was measured  first using TT7000 signal meter/counter and later to verify the measurements with a calibrated Rohde & Schwarz FPC1500 spectrum analyzer.

## Structure
* `logs` - this directory contains recorded values measured during the tests
* `py` - python script for processing the logged data
* `py/out` - directory for script outputs (not pushed to the repo)
* `src` - C++ sources for collecting the measured data and verifying the optimized PA configuration

## Dependencies
To build and run the measurements, [dc-powermon](https://github.com/radiolib-org/dc-powermon) and [rf-powermon](https://github.com/radiolib-org/rf-powermon). Running the `measure.cpp` program also requires a modified version of RadioLib that allows to directly configure set the PA configuration and the `lgpio` library to run RadioLib on Raspberry Pi.

## Test setup
The SX126x under test was inserted into the RadioHAT and its RF output connected to the RF power meter through a 30 dBm attenuator. The RPi was also connected to the RF power meter, either via a USB cable (for TT7000), or to the same local network as the spectrum analyzer. On the RPi, the dc-powermon client was started to measure the DC power consumption via the INA219. The test is then prepared by building the binary with `./build.sh src/measure.cpp` and then executed by calling `./repeat.sh`. This will continue executing the test until killed.

One iteration of the test takes approximately 30 minutes, mainly due to the number of possible configurations that must be tested and the time spent waiting for the RF output level to stabilize.

## Data processing & outputs
The measured data was processed using the `py/process.py` script. It takes the input CSV log files and produces an output CSV file with determined optimized PA configurations, as well as a code snippet of the optimized PA lookup table usable in RadioLib. For the processing logic, see the script itself. To run the script, you just have to `cd py` and then `python .\process.py ../logs/measure`
