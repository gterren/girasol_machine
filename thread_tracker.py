"""
SOLAR TRACKING SYSTEM CODE. THIS CODE IS IMPLEMENTE FOR AND USING
COMMAND FLIR-E46 PROTOCOL.

Suns coordinates generatated using lib_sun_position.py - library

    v. 7:
        - Timeout Socket Error catched
            + Tracking system not found error
        - Time sleep added before restarting
        - Send an email when Erro is catched
        - Summer highest position reachs to sun
        - Track limits on tilt limit error fixed
	- New library lib_sun_position_v6.py that corrects tracking files

DEVELOPED BY G.TERREN
"""

import socket, threading

from datetime import datetime
from sys import exit, argv, executable
from time import time, sleep, localtime
from numpy import around, absolute, sign, savetxt
from multiprocessing import Queue, Manager
from os import path, makedirs, system, listdir, remove, execv
from glob import glob
from shutil import move
from warnings import filterwarnings

import lib_sun_position as libsun

filterwarnings('ignore')

# TRACKER SPECIFICATIONS
PAN_STEP  = 0.051429
TILT_STEP = 0.051429
PAN_MAX   = 3098
PAN_MIN   = -3098
TILT_MAX  = 591
TILT_MIN  = -907
# SAVES IMAGES IN THE FOLLOWING PATH
path_source = '/home/girasol/girasol_project/source/'
path_data   = '/home/girasol/girasol_project/data/'
path_temp   = '/home/girasol/girasol_project/temp/'
path_queue  = '/home/girasol/girasol_project/real_time_queue/'
# COMMUNICATION SPECIFICATIONS
TCP_IP      = '192.168.0.104'
TCP_PORT    = 4000
TRACKER_BUFFER_SIZE = 1024
BUFFER_SIZE = 1
# Tracker Configuration list
axisStep_  = [PAN_STEP, TILT_STEP]
axisLimit_ = [PAN_MAX, PAN_MIN, TILT_MAX, TILT_MIN]
comm_      = [TCP_IP, TCP_PORT, TRACKER_BUFFER_SIZE]

# CALCULATE TRACKER ROTATION
def _tracking_angles(AZA, EA):
    # ADJUST THE ERROR IN THE TRACKING PAN AND TILT !! 180 AND 48 BY DEFAULT
    # THIS MUST BE ADJUTS IFNOT RIGHT, IT IS POSITIVE THIS MUST BE ADJUST ACCORDING
    PA = around((-AZA  + 180.) / axisStep_[0], 0)
    TA = around((EA - 46.) / axisStep_[1], 0)
    # TO CAMERA SUPPORT ANGLE, IT IS NEGATIVE! STAYS ON THE LIMITS
    if PA > axisLimit_[0] or PA < axisLimit_[1]:
        if PA > axisLimit_[0]:
            PA = axisLimit_[0]
        else:
            PA = axisLimit_[1]
    if TA > axisLimit_[2] or TA < axisLimit_[3]:
        if TA > axisLimit_[2]:
            TA = axisLimit_[2]
        else:
             TA = axisLimit_[3]
    return int(PA), int(TA)

# ITILIALIZES SOCKET AND CLEANS UP BUFFER
def _open_socket():
    data_ = ''
    flag  = True
    try:
        # Open Socker
        _s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _s.settimeout(3)
        _s.connect((comm_[0], comm_[1]))
        # Empty Socket
        while flag:
            data_ += _s.recv(comm_[2])
            if len(data_) > 123: flag = False
        print('>> Opened Socket')
        return _s
    except:
        print('ERROR: TRACKER SYSTEM NOT FOUND!')
        exit()

def _close_socket(_s):
    _s.close()
    print('>> Closed Socket')

# SENDS COMMANDS TO TRACKER
def _send_command(_s, command_):
    data_ = ''
    _s.sendall(command_)
    while True:
        try:
            data_ += _s.recv(comm_[2])
            if data_.find(command_[1:-1]) == 0:
                break
        except:
            print('ERROR: COMMUNITAION SENDING')
            break

# SPLITS UP A MESSAGE INTO COMMANDS
def _send_message(_s, message):
    for command in message:
        _send_command(_s, command)

# GET THE ACTUAL POSITION OF THE TRACKING AXES
def _camera_position(_s):
    PP = 0
    TP = 0
    flag = False

    for command_ in (' PP ', ' TP '):
        data_ = ''
        _s.sendall(command_)
        while not flag:
            try:
                data_ += _s.recv(comm_[2])
                if data_[:14] == 'PP * Current P':
                    PP = int(data_[29:len(data_) - 2])
                    break
                if data_[:14] == 'TP * Current T':
                    TP = int(data_[30:len(data_) - 2])
                    break
            except:
                print('ERROR: COMMUNITAION IN POSITION')
                flag = True
    return PP, TP, flag

def _y_axis_model(y_, b_1 = 0.003382460519458059, b_0 = 1.425, rho = 4.105076070296965):
    # rho = 115.7085 # steps per pixel
    # [[-1.42831270e-04]
    #  [ 4.07516624e-01]]
    x_ = y_ * b_1 + b_0
    x_ = x_ * rho #* 1.5
    return x_

def _x_axis_model(x_, b_1 = - 0.006051983351737022, b_0 = 7.20900378514397, rho = 4.105076070296965):
    # rho = 115.7085 # steps per pixel
    # [[-7.14402677e-04]
    #  [-1.84133341e+00]]
    y_ = x_ * b_1 + b_0
    y_ = y_ * rho #/ 2.75
    return - y_

# GO HOME AND SET SPEED AND ACELERATION TO DEFAULT
def _next_position(_s, PA, TA, PP, TP, flag, bias_, WT):
    # Inc. Position
    IP_ = [int(around(PA - PP + bias_[0])), int(around(TA - TP + bias_[1]))]
    # Velocity Rotation
    VR_ = [int(absolute(around(IP_[0]/WT))), int(absolute(around(IP_[1]/WT)))]
    if VR_[0] != 0 and not flag:
        _send_message(_s, message = (' PA250 ', ' PS{} '.format(str(VR_[0])),' PO{} '.format(str(IP_[0]))))
        sleep(WT)
    if VR_[1] != 0 and not flag:
        _send_message(_s, message  = (' TA250 ', ' TS{} '.format(str(VR_[1])), ' TO{} '.format(str(IP_[1]))))
        sleep(WT)
    return PP, TP, flag

def _rotate_tracker(_s, _tr_thread_flag):
    def __add_sample(data_):
        # if queue is full empty it and put it on the que
        if q.full():
            while not q.empty():
                q.get_nowait()
        # put it in the queue
        q.put(data_)
    while not _tr_thread_flag.is_set():
        try:
            # Select bias on rotational tracking axis and get time
            bias_ = _tr_thread_flag.bias_
            unix_ = time()
            time_ = datetime.fromtimestamp(unix_).strftime('%H:%M:%S.%f')
            # Calculate Angles and Rotate Tracker
            EA, AZA = libsun._get_sun_position(unix_, save = False)
            PA, TA  = _tracking_angles(AZA, EA)
            # Camera Position
            PP, TP, flag = _camera_position(_s)
            #print(_x_axis_model(PP), _y_axis_model(TP))
            # Calculate Bias
            PB = 0. # _y_axis_model(TP)
            TB = 0. # _x_axis_model(PP)
            if EA > 0.:
                PP, TP, flag = _next_position(_s, PA, TA, PP, TP, flag, bias_ = [PB, TB], WT = .2)
                __add_sample(data_ = [PP, TP, PA, TA, PB, TB, unix_, time_, flag])
            else:
                __add_sample(data_ = [0., 0., 0., 0., 0., 0., unix_, time_, False])
            sleep(2.)
        except:
            __add_sample(data_ = [None, None, None, None, None, None, None, None, True])
            print('ERROR: Threading Error!')
            pass

# Save a Data Sample
def _save_data(x, y, unix_, name, path):
    with open(name = '{}{}.csv'.format(path, name), mode = 'a') as f:
        savetxt(f, [x], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [y], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [unix_], delimiter = '', fmt = "%s", newline = ',')

# Get a samples in the Queue
def _get_queue(unix_, display):
    try:
        data_ = q.get(timeout = 5)
        if display and not data_[-1]:
            print('>> Tracker Pan: {} Tilt: {} Objective Pan: {} Tilt: {} Bias Pan: {} Bias Tilt: {} Unix: {} Time: {} Name: {}'.format(data_[0], data_[1], data_[2], data_[3], data_[4], data_[5], data_[6], data_[7], unix_) )
            _save_data(data_[0], data_[1], unix_, name = 'TR', path = path_queue)
        return data_[-1]
    except:
        print('ERROR: Reading TR-Queue Error!')
        return True

def _start_threads(_s):
    _tr_thread_flag = threading.Event()
    _tr_thread_flag.bias_ = [3, 2]
    _tr_thread_flag.flag = True
    _tr_thread = threading.Thread(target = _rotate_tracker, args = (_s, _tr_thread_flag))
    _tr_thread.start()
    return _tr_thread_flag

def _kill_threads(_tr_thread_flag):
    _tr_thread_flag.set()

def _download_weather_station_data(name):
    year, month, date = name.split('_')
    system(r'sudo python {}get_weather_station_data.py {} {} {}'.format(path_source, year, month, date))

def _save_files(save, save_files, DAQ = True, COMP = True, DEL = True, QUEUE = True, WS = True):
    if save and not save_files:
        sleep(10800.)
        try:
            if QUEUE:
                for f in glob( '{}*'.format(path_queue) ):
                    remove(f)
            name = datetime.fromtimestamp(time()).strftime('%Y_%m_%d')
            new_folder_path = path.join(path_data, name)
            if WS:
                _download_weather_station_data(name)
            if DAQ:
                if not path.exists(new_folder_path):
                    makedirs(new_folder_path)
                for file_name in listdir(path_temp):
                    move(path.join(path_temp, file_name), new_folder_path)
                if COMP:
                    system('sudo tar -zcvf {}.tar.gz {}'.format(new_folder_path, new_folder_path))
                    if DEL:
                        system('sudo rm -rf {}'.format(new_folder_path))
        except:
            print('ERROR: NO FREE SPACE IN THE DISK')
            pass

def _init():
    _s = _open_socket()
    _tr_thread_flag = _start_threads(_s)
    return _s, _tr_thread_flag

def _kill(_tr_thread_flag, _s):
    _kill_threads(_tr_thread_flag)
    _close_socket(_s)

def _reset(_tr_thread_flag, _s):
    print('>> Reset Tracker')
    print('>> Reset Pyranometer')
    try:
        _kill(_tr_thread_flag, _s)
    except:
        pass
    execv(executable, ['python'] + argv)

# Run tracker and save files!
def _main(save = False, display = False, min_elevation = 0, freq = 15):

    _s, _tr_thread_flag = _init()
    save_files = False

    while True:
        try:
            # get current elevation angle
            diff = 1.
            unix_ = time()
            elevation = libsun._get_sun_position(unix_, save = False)[0]
            # Daylight session is not save
            if elevation > min_elevation:
                unix_ = around(unix_)
                if divmod(around(unix_), freq)[1] == 0:
                    save_files = False
                    flag = _get_queue(unix_, display)
                    if flag: _reset(_tr_thread_flag, _s)
                    diff = unix_ - time() + freq
            # If is not day sassion save it
            else:
                # iff session has not been saved yet!
                _save_files(save, save_files)
                save_files = True
            sleep(diff)
        except:
            break

    _kill(_tr_thread_flag, _s)

def _setup():
    sleep(20.)

# Queue Initialization
q = Queue(BUFFER_SIZE)

if __name__ == '__main__':
    _setup()
    _main(save = True, display = True, min_elevation = 15, freq = 15)
