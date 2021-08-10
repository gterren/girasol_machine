# -*- coding: utf-8 -*-
"""
CODE FOR READING A SERIAL PORT IN UBUNTU. DEVICE CONNECTED
IS A PYRANOMETER ATTACHED TO A ARDUINO BOARD AND AN ANALOG
TO DIGTAL CONVERTER.

DEVELOPED BY G.TERREN
"""

import serial, threading

from time import time, sleep, strftime
from sys import exit, argv, executable
from numpy import savetxt, around
from os import system, path, execv
from glob import glob
from datetime import datetime
from multiprocessing import Queue, Manager
from warnings import filterwarnings

import lib_sun_position as libsun

filterwarnings('ignore')

# SAVES IMAGES IN THE FOLLOWING PATH
path_temp  = '/home/girasol/girasol_project/temp/'
path_queue = '/home/girasol/girasol_project/real_time_queue/'
# PARAMATERS FOR SERIAL COMMUNITAION IN UBUNTU AND PYTHON
nameUSB = '/dev/ttyACM0'; rateUSB = 9600
comm_   = [nameUSB , rateUSB]
# CONFIGURATION
BUFFER_SIZE = 10

# Open Serial Port
def _open_port():
    def __open_error():
        print('ERROR: CANNOT OPEN SERIAL PORT')
        exit()
    try:
        _ser = serial.Serial(comm_[0], comm_[1], timeout = 1)
        if _ser.isOpen():
            print('>> Opened port')
            return _ser
        else: __open_error()
    except: __open_error()

# Close Serial Port
def _close_port(_ser):
    _ser.close()
    print('>> Closed Port')
    #exit()

# Save a Data Sample
def _save_sample(data_, unix_, time_, name, path):
    with open(name = '{}{}.csv'.format(path, name), mode = 'a') as f:
        savetxt(f, [data_[0]], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [data_[1]], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [data_[2]], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [unix_], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [time_], delimiter = '', fmt = "%s", newline = '\n')

# Main pyranometer measurements grabber
def _pyranometer_sampler(_ser, _py_thread_flag):
    # pyranometer samples grabber
    def __get_sample(_ser):
        # Read if port is available
        if _ser.readable():
            data_ = _ser.readline()
            # If reading was not correct rise a flag
            if data_ == '':
                data_ = 0
                flag  = True
            # otherwise keep down the Flag
            else:
                flag = False
        # otherwise rise a Flag
        else:
            data_ = 0
            flag  = True
        # get current time
        unix_ = time()
        time_ = datetime.fromtimestamp(unix_).strftime('%H:%M:%S.%f')
        return float(data_), unix_, time_, flag
    # Add Sample to the queue
    def __add_sample(data_):
        # if queue is full empty it and put it on the que
        if q.full():
            while not q.empty():
                try: q.get_nowait()
                except: break
        # put it in the queue
        q.put(data_)

    while not _py_thread_flag.is_set():
        try:
            PY, unix_, time_, flag = __get_sample(_ser)
            EA, AZA = libsun._get_sun_position(unix_)
            __add_sample(data_ = [PY, EA, AZA, unix_, time_, flag])
        except:
            __add_sample(data_ = [None, None, None, None, None, True])
            print('ERROR: Threading Error!')
            pass
        #sleep(.25)

def _start_threads(_ser):
    _py_thread_flag = threading.Event()
    _py_thread = threading.Thread(target = _pyranometer_sampler, args = (_ser, _py_thread_flag))
    _py_thread.start()
    return _py_thread_flag

def _kill_threads(_py_thread_flag):
    _py_thread_flag.set()

# Empty Queue with several elements
def _empty_queue():
    queue_ = []
    while True:
        try:
            queue_.append(q.get_nowait())
        except:
            break
    return queue_

# Average all elements on a queue
def _average_data(queue_):
    N = len(queue_)
    PY  = 0
    EA  = 0
    AZA = 0
    unix_ = 0
    flag  = False
    for data_ in queue_:
        PY    += data_[0]/N
        EA    += data_[1]/N
        AZA   += data_[2]/N
        unix_ += data_[3]/N
        if data_[5]: flag = True
    time_ = datetime.fromtimestamp(unix_).strftime('%H:%M:%S.%f')
    return [PY, EA, AZA, unix_, time_, flag]

# Get a samples in the Queue
def _get_queue(unix_, save_local, save_real_time, display):
    try:
        #data_ = q.get(timeout = 5)
        data_ = _average_data(_empty_queue())
        time_ = datetime.fromtimestamp(unix_).strftime('%H:%M:%S.%f')
        if save_local and not data_[-1]:
            _save_sample(data_, unix_, time_, strftime("%Y-%m-%d"), path_temp)
        if save_real_time and not data_[-1]:
            _save_sample(data_, unix_, time_, strftime("%Y-%m-%d"), path_queue )
        if display and not data_[-1]:
            print('>> Masurement: {} Elevation: {} Azimuth: {} Unix: {} Time: {} Name: {}'.format(data_[0], data_[1], data_[2], data_[3], data_[4], unix_) )
        return data_[-1]
    except:
        print('ERROR: Reading PY-Queue Error!')
        return True

def _init():
    _ser = _open_port()
    _py_thread_flag = _start_threads(_ser)
    return _ser, _py_thread_flag

def _kill(_py_thread_flag, _ser):
    _kill_threads(_py_thread_flag)
    _close_port(_ser)

def _reset(_py_thread_flag, _ser):
    print('>> Reset Pyranometer')
    try:
        _kill(_py_thread_flag, _ser)
    except:
        pass
    execv(executable, ['python'] + argv)

def _main(save_local, save_real_time, display, min_elevation, freq):

    _ser, _py_thread_flag = _init()
    while True:
        try:
            # get current elevation angle
            diff = 1.
            unix_ = time()
            elevation = libsun._get_sun_position(unix_, save = False)[0]
            if elevation > min_elevation:
                unix_ = around(unix_)
                if divmod(unix_, freq)[1] == 0:
                    flag = _get_queue(unix_, save_local, save_real_time, display)
                    if flag: _reset(_py_thread_flag, _ser)
                    diff = unix_ - time() + freq
                    #print(unix_, flag, time(), diff)
            sleep(diff)
        except:
            break

    _kill(_py_thread_flag, _ser)

def _setup(usb):
    system('sudo ykushcmd -d {}'.format(usb) )
    sleep(5.)
    system('sudo ykushcmd -u {}'.format(usb) )
    sleep(20.)

# Queue Initialization
q = Queue(BUFFER_SIZE)

if __name__ == '__main__':
    _setup(usb = 3)
    _main(save_local = True, save_real_time = True, display = True, min_elevation = 15, freq = 1)
