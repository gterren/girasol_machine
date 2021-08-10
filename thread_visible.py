'''
THIS CODE CAPTURES FRAMES FROM A VISIBLE CAMERA FOR AND USING
ELP FOV120 FISHEYE SENSOR. IMPLEMENTATION OF CAPTURE SESION
PARAMETRIZATION AND SENSOR CONFIGUREATION.

ERROR: _find_device() does not work always, so camera device is incorrect. Whilist not reboot device works.
ERROR: This device is not conneceted to the switch hub, so hard-reset functionality is not available
v.6:
    - Image Fusion Algorithm added.
    - Stopping email notification.
    - Code robustest increased.
    - Remove saving on dir 4 exposures images.

DEVELOPED BY G.TERREN
'''

import cv2, png, re, subprocess, threading

from datetime import datetime
from time import sleep, time
from sys import exit, argv, executable
from numpy import isnan, mean, where, zeros, around, invert, savetxt
from signal import alarm
from os import system, path, execv
from multiprocessing import Queue, Manager
from keyboard import is_pressed, wait, read_key
from warnings import filterwarnings

import lib_sun_position as libsun
import lib_image_fusion as libfusion

filterwarnings('ignore')

# SAVES IMAGES IN THE FOLLOWING PATH
path_temp  = '/home/girasol/girasol_project/temp/'
path_queue = '/home/girasol/girasol_project/real_time_queue/'
# CONFIGURATION IN THE RANGE OF EXPOSURES
exposureConfig_ = [1, 4, 12, 28]
NO_EXPS = 4
NO_CAPS = 8
CAMERA_BUFFER_SIZE = 4
BUFFER_SIZE = 1
viConfig_ = [NO_EXPS, NO_CAPS, CAMERA_BUFFER_SIZE]
# INITIALIZATION OF FUSION LIBRARY
_fusion = libfusion._fusion(path_temp)

# Save 16bits Image
def _save_image(data_, name, path):
    with open('{}{:010}VI.png'.format(path, int(name)), 'wb') as f:
        writer = png.Writer(width = 450, height = 450, bitdepth = 16, compression = None, greyscale = True)
        writer.write(f, data_)
        #writer.write(f, data_[15:465, 95:545].tolist())

# Save the four-exposure images
def _save_exposures(data_, name, path):
    for i in range(data_.shape[0]):
        cv2.imwrite('{}{}VI{}.png'.format(path, int(name), i), _fusion._white_balance(data_[i, ...]), [cv2.IMWRITE_PNG_COMPRESSION, 0])

# Fusion the captures
def _main_fusion(data_):
    _fusion._update(data_)
    libfusion._merge_visible(_fusion)
    return _fusion._return()

# Find the Sun's position in the frame
def _sun_position(I_, sun_pixels = 60000.):
    x_ = where(I_ >= sun_pixels)
    xc = mean(x_[1])
    yc = mean(x_[0])
    if isnan(xc) or isnan(yc):
        xc = 225.
        yc = 225.
    x_p = xc - 225.
    y_p = yc - 225.
    print(I_.max(), I_.min())
    return x_p, y_p
    #print('>> VI. OFFSET: X = {} Y = {} [%]'.format( x_p, y_p) )

# Open Visible Camera
def _open_camera(mode):
    # Identify which of the connected cameras, it is the visible
    def __find_device():
        dev_1_name = 'HD USB Camera'
        dev_2_name = 'PureThermal 1'
        for line in subprocess.check_output(['sudo', 'uvcdynctrl', '-l']).split('\n'):
	    if line.find(dev_1_name) > 0 and line.find('video') > 0:
		idx = line.find('video')
		_dev = int(line[idx + 5:idx + 6])
        return _dev

    # Set Visible Camera Configuration in manual to access to the raw camera pixels
    def __set_mode(_dev, mode = 'manual'):
        if mode is 'manual':
            system('sudo uvcdynctrl -d video{} --set "Exposure, Auto" 1'.format(_dev))
            system('sudo uvcdynctrl -d video{} --set "White Balance Temperature, Auto" 0'.format(_dev))
            print('>> Visible camera raw pixels: ON')
        else:
            system('sudo uvcdynctrl -d video{} --set "Exposure, Auto" 3'.format(_dev))
            system('sudo uvcdynctrl -d video{} --set "White Balance Temperature, Auto" 1'.format(_dev))
            print('>> Visible camera raw pixels: OFF')
    try:
        _dev = __find_device()
        _cam = cv2.VideoCapture(_dev)
        __set_mode(_dev, mode)
        print('>> Opened Visible')
        return _cam, _dev
    except:
        print('ERROR: VISIBLE CAMERA CANNOT OPEN.')
        exit()

# Close Safely Camera Device
def _close_camera(_cam):
    alarm(5)
    try:
        _cam.release()
        print('>> Closed Visible')
    except:
        print('ERROR: VISIBLE CAMERA CANNOT CLOSE.')
        exit()

# System Command To change Exposure
def _adjust_exposure(_dev, i):
    system('sudo uvcdynctrl -d video{} --set "Exposure (Absolute)" {}'. format(_dev, exposureConfig_[i])) ## 0 - 5000
    # Change is not inmediate, so it requieres a waiting time for changes to be effective ve
    sleep(.2)

# System Command Display all camera divice control options
def _get_controls(_dev):
    system('sudo uvcdynctrl -d video{} --clist'.format(_dev))

# Main visible images grabber
def _visible_sampler(_cam, _dev, _vi_thread_flag):
    # visible images grabber
    def __get_image(_cam):
        # Initilize variable
        data_ = zeros((viConfig_[0], viConfig_[1], 480, 640, 3))
        # Get Differnet Exposure-time images
        for i in range(viConfig_[0]):
            # Change cameras exposure time
            _adjust_exposure(_dev, i)
            # Empty Reading camera port buffer
            for _ in range(viConfig_[2]):
                _ = _cam.read()
            # Get Several Frames of Noise Attenuation
            for ii in range(viConfig_[1]):
                flag, data_[i, ii, ...] = _cam.read()
        # get current time
        unix_ = time()
        time_ = datetime.fromtimestamp(unix_).strftime('%H:%M:%S.%f')
        return mean(data_, axis = 1), unix_, time_, invert(flag)
    # Add Sample to the queue
    def __add_sample(data_):
        # if queue is full empty it and put it on the que
        if q.full():
            while not q.empty():
                try: q.get_nowait()
                except: break
        # put it in the queue
        q.put(data_)
    # Thread loop
    while not _vi_thread_flag.is_set():
        try:
            images_, unix_, time_, flag = __get_image(_cam)
            __add_sample(data_ = [images_, unix_, time_, flag])
        except:
            __add_sample(data_ = [None, None, None, True])
            print('ERROR: Threading Error!')
            pass

# Threading Visible Captures
def _start_threads(_cam, _dev):
    _vi_thread_flag = threading.Event()
    _vi_thread = threading.Thread(target = _visible_sampler, args = (_cam, _dev, _vi_thread_flag))
    _vi_thread.start()
    return _vi_thread_flag

# Stop Safely Threading
def _kill_threads(_vi_thread_flag):
    alarm(5)
    try: _vi_thread_flag.set()
    except: pass

# Save a Data Sample
def _save_data(x, y, unix_, name, path):
    with open(name = '{}{}.csv'.format(path, name), mode = 'a') as f:
        savetxt(f, [x], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [y], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [unix_], delimiter = '', fmt = "%s", newline = ',')

# Get a samples in the Queue
def _get_queue(unix_, save_local, save_real_time, display):
    try:
        data_ = q.get(timeout = 5)
        image_ = _main_fusion(data_[0])
        if save_local and not data_[-1]:
            _save_image(image_, unix_, path_temp)
        if save_real_time and not data_[-1]:
            _save_image(image_, unix_, path_queue)
            #_save_exposures(data_[0], data_[1], path = path_queue)
        if display and not data_[-1]:
            x, y = _sun_position(image_, sun_pixels = 50000.)
            print('>> x_sun: {}  y_sun: {} Unix: {} Time: {} Name: {}'.format(x, y, data_[1], data_[2], unix_) )
            _save_data(x, y, unix_, name = 'VI', path = path_queue)
        return data_[-1]
    except:
        print('ERROR: Reading VI-Queue Error!')
        return True

def _init():
    _cam, _dev = _open_camera(mode = 'manual')
    _vi_thread_flag = _start_threads(_cam, _dev)
    return _cam, _dev, _vi_thread_flag

def _kill(_vi_thread_flag, _cam):
    _kill_threads(_vi_thread_flag)
    _close_camera(_cam)

def _reset(_vi_thread_flag, _cam):
    print('>> Reset Visible')
    try:
        _kill_threads(_vi_thread_flag)
        _cam.release()
    except:
        pass
    execv(executable, ['python'] + argv)

def _main(save_local, save_real_time, display, min_elevation, freq):

    _cam, _dev, _vi_thread_flag = _init()

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
                    if flag: _reset(_vi_thread_flag, _cam)
                    diff = unix_ - time() + freq - 0.014
                    #print(unix_, flag, time(), diff)
            sleep(diff)
        except:
            break

    _kill(_vi_thread_flag, _cam)

def _setup(usb):
    system('sudo ykushcmd -d {}'.format(usb) )
    sleep(5.)
    system('sudo ykushcmd -u {}'.format(usb) )
    sleep(20.)

# Queue Initialization
q = Queue(BUFFER_SIZE)

if __name__ == '__main__':
    _setup(usb = 1)
    _main(save_local = True, save_real_time = True, display = True, min_elevation = 15, freq = 15)
