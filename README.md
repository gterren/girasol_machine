# Girasol Machine

This repository contains the software implemented in the Girasol Machine.

See article: https://www.sciencedirect.com/science/article/pii/S2352340921001980

The Girasol Machine is an sky imager that is mounted on a solar tracker. It was developed to acquire infrared and visible sky images, pyranometer measurements and weather features from a nearby weather station.

This repository contains the dependecies requiered for running the Girasol Machine: visible image fusion software, sun position in the sky software and lepton camera drivers.

## Sofware

The software is run through run_girasol_machine.py file. The adquisition is threaded in multple CPUs if available. 

The infrared images are adquired by thread_infrared.py and the pyranometer measurements using thread_pyranometer.py. 

The functions and drivers of the infrared camera are in lib_lepton_camera.py. The software required to commit and build /libuvc and /purethermal1-uvc-capture. This dependencies are requiered by purethermal board 1, where the Lepton 2.5 is installed. 

The multi-exposure fisheye images are acquired from the visible camera thread_visible.py and the fusion algorithm is implemented in lib_image_fusion.py. 

The solar tracker is controlled with thread_tracker.py and the sun position is calculated usisng the solar time aglorithm in lib_sun_position.py.

The weather features are retrived from an real time repository of a nearby weather station using this code get_weather_station_data.py.

## Hardware

The reset is performed using: https://www.yepkit.com/products/ykush.
To run the reset will requiered to commit and build the software when this device is used.

The infrared camera Lepton 2.5 is installed in a purethermal 1 board: https://groupgets.com/manufacturers/getlab/products/purethermal-1-flir-lepton-smart-i-o-module. See Lepton 2.5 here: https://www.flir.com/products/lepton/

The solar tracker is a PTU-e46, the software is meant to operate with its control unit: https://www.flir.com/products/ptu-e46/

The pyranometer is a LI-200R https://www.licor.com/env/products/light/pyranometer, and it is connected to an Artuino https://www.arduino.cc for signal anolog to digital conversion purporses. The signal is filtered and amplified prior to enter the arduino.

## Dataset

A sample dataset is publicaly available in DRYAD repository: https://datadryad.org/stash/dataset/doi%253A10.5061%252Fdryad.zcrjdfn9m
