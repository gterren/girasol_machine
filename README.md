# girasol_machine

This repository contains the software implemented in the Girasol Machine.

See article: https://www.sciencedirect.com/science/article/pii/S2352340921001980

The Girasol Machine is mounted on a solar tracker and it was developed to acquire infrared and visible sky images, pyranometer measurements and weather features from a nearby weather station.

This repository contains the dependecies requiered for running the Girasol Machine: visible image fusion software, sun position in the sky software and lepton camera drivers.

## Hardware

The reset is performed using: https://www.yepkit.com/products/ykush.
To run the reset will requiered to commit and build the software when this device is used.

The infrared camera Lepton 2.5 is installed in a purethermal 1 board: https://groupgets.com/manufacturers/getlab/products/purethermal-1-flir-lepton-smart-i-o-module. See Lepton 2.5 here: https://www.flir.com/products/lepton/

The solar tracker is a PTU-e46, the software is meant to operate with its control unit: https://www.flir.com/products/ptu-e46/

The pyranometer is a LI-200R https://www.licor.com/env/products/light/pyranometer, that is connected to a artuino https://www.arduino.cc for digital an anolog converter purporses.
