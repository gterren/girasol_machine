"""
CROSS-CORRELATION ANALYSIS IN A SEQUENCE OF IMAGES TO
AVOID OUTLIERS AND NOISE ATTENUATION.

v.5:
    - Removing original folder after compression.
    - Cleaning Code.
    - Code robustest increased.

DEVELOPED BY G.TERREN
"""


import threading, png

from ctypes import *
from datetime import datetime
from multiprocessing import Process, Queue, Manager
from scipy.stats import pearsonr
from sys import exit, argv, executable
from signal import alarm
from time import sleep, time
from os import system, path, execv
from numpy import zeros, frombuffer, dtype, uint16, mean, where, isnan, around, array, newaxis, asarray, reshape, append, unique, delete, arange, sum, max, savetxt
from lib_lepton_camera import *
from warnings import filterwarnings

import lib_sun_position as libsun

filterwarnings('ignore')

# SAVES IMAGES IN THE FOLLOWING PATH
path_temp   = '/home/girasol/girasol_project/temp/'
path_source = '/home/girasol/girasol_project/source/'
path_queue  = '/home/girasol/girasol_project/real_time_queue/'
# CONFIGURATION
NO_CAP = 10
BUFFER_SIZE = 1
CORR_ANALYSIS = True

def _save_image(data_, name, path):
    with open('{}{:010}IR.png'.format(path, int(name)), 'wb') as f:
        writer = png.Writer(width = data_.shape[1], height = data_.shape[0], bitdepth = 16, compression = None, greyscale = True)
        writer.write(f, data_)
        #writer.write(f, around(data_, 0).tolist())

def _sun_position(I_, sun_pixels = 45055.):
    x_ = where(I_ >= sun_pixels)
    xc = mean(x_[1])
    yc = mean(x_[0])
    if isnan(xc) or isnan(yc):
        xc = 40.
        yc = 30.
    #x_p = 100.*(xc - 40.)/80.
    #y_p = 100.*(yc - 30.)/60.
    x_p = xc - 40.
    y_p = yc - 30.
    print(I_.max(), I_.min())
    return x_p, y_p
    #print('IR. OFFSET: X = {} Y = {} [%]'.format( x_p, y_p))

def _open_camera():
    cam_ = []
    try:
        ctx  = POINTER(uvc_context)()
        devh = POINTER(uvc_device_handle)()
        dev  = POINTER(uvc_device)()
        ctrl = uvc_stream_ctrl()

        if libuvc.uvc_init(byref(ctx), 0) < 0:
            print("ERROR: uvc_init")
            exit()
        if libuvc.uvc_find_device(ctx, byref(dev), 0, 0, 0) < 0:
            print("ERROR: uvc_find_device")
            exit()
        if libuvc.uvc_open(dev, byref(devh)) < 0:
            print("ERROR: uvc_open")
            exit()

        libuvc.uvc_get_stream_ctrl_format_size(devh, byref(ctrl), UVC_FRAME_FORMAT_Y16, 80, 60, 9)

        cam_.append(ctx)
        cam_.append(dev)
        cam_.append(devh)
        cam_.append(ctrl)
        print('>> Opened Infrared')
        return cam_
    except:
        print('ERROR: INFRARED CAMERA CANNOT OPEN')
        exit()

def _start_threads(cam_):
    _ir_thread_flag = threading.Event()
    _ir_thread_flag.cam_ = cam_
    _ir_thread_flag.res_ = libuvc.uvc_start_streaming(cam_[2], byref(cam_[3]), PTR_PY_FRAME_CALLBACK, None, 0)
    return _ir_thread_flag

def _kill_threads(_ir_thread_flag):
    alarm(5)
    try:    libuvc.uvc_stop_streaming(_ir_thread_flag.cam_[2])
    except: pass

def _close_camera(cam_):
    alarm(5)
    try:
        libuvc.uvc_stop_streaming(cam_[2])
        libuvc.uvc_unref_device(cam_[1])
        libuvc.uvc_exit(cam_[0])
        print('>> Closed Infrared')
    except:
        print('ERROR: INFRARED CAMERA CANNOT CLOSE')
        pass
    exit()
# Thread loop function
def py_frame_callback(frame, userptr):
    # Find Highly Correlated Frames that could be errors..
    def __corr(data_, rho):
        def ___non_unique(idx_, no_min_corr_images = 3):
            #print(idx_)
            unq_, _, unq_counts_ = unique(idx_, return_inverse = True, return_counts = True)
            unq_ = unq_.astype(int)
            #print(unq_)
            M = np.max(unq_counts_)
            idx_ = unq_counts_ < M
            print(unq_, unq_counts_, idx_.sum(), M)
            idx_ = unq_[idx_]
            return delete(unq_, idx_)
        idx_ = []
        for i in range(data_.shape[0]):
            #print(i, _sun_position(data_[i, ...], sun_pixels = 45000.))
            for j in range(data_.shape[0]):
                R, _ = pearsonr(asarray(data_[i, ...]).reshape(-1), asarray(data_[j, ...]).reshape(-1))
                #print(i, j, R, _sun_position(data_[i, ...], sun_pixels = 45000.), _sun_position(data_[j, ...], sun_pixels = 45000.))
                if R > rho and R != 1.0:
                    idx_ = append(idx_, j)
        idx_ = ___non_unique(idx_)
        #print(idx_)
        if idx_.shape[0] > 0:
            return mean(data_[idx_, ...], axis = 0), False
        else:
            print('Low Correlation!')
            #return mean(data_, axis = 0), True
            return None, True

    # Camculate the Error metric between 2 consecutive frames
    def __compare_frames(I_1_, I_2_):
        return sum( (I_1_.astype('float') - I_2_.astype('float')) ** 2) # / float(I_1_.shape[0] * I_2_.shape[1])
    # Add Sample to the queue
    def __add_sample(data_):
        # if queue is full empty it and put it on the que
        if q.full():
            while not q.empty():
                try: q.get_nowait()
                except: break
        # put it in the queue
        q.put(data_)
    # visible images grabber
    def __get_image(frame, userptr):
        i = 0
        data_  = zeros((NO_CAP, 60, 80))
        f_prv_ = zeros((60, 80))
        while i < NO_CAP:
            array_pointer = cast(frame.contents.data, POINTER(c_uint16 * (frame.contents.width * frame.contents.height)))
            f_now_ = frombuffer(array_pointer.contents, dtype = dtype(uint16)).reshape(frame.contents.height, frame.contents.width)
            # Check if the last retrive frame is the same that the previous frame
            e = __compare_frames(f_now_, f_prv_)
            if e != 0.:
                # Save Frame if it is good
                data_[i, ...] = f_now_.copy()
                f_prv_ = f_now_.copy()
                i += 1
            sleep(.15)
        # get current time
        unix_ = time()
        time_ = datetime.fromtimestamp(unix_).strftime('%H:%M:%S.%f')
        # Remove not Correlate Data (Shutter problem in capture)
        if CORR_ANALYSIS:
            data_, flag = __corr(data_, rho = .9)
        # Mean over samples
        else:
            data_ = mean(data_, axis = 0)
            flag  = False
        return data_, unix_, time_, flag

    try:
        image_, unix_, time_, flag = __get_image(frame, userptr)
        if not flag: __add_sample(data_ = [image_, unix_, time_, flag])
        sleep(2.)
    except:
        __add_sample(data_ = [None, None, None, True])
        print('ERROR: Captures!')
        pass

# Save a Data Sample
def _save_data(x, y, unix_, name, path):
    with open('{}{}.csv'.format(path, name), mode = 'a') as f:
        savetxt(f, [x], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [y], delimiter = '', fmt = "%s", newline = ',')
        savetxt(f, [unix_], delimiter = '', fmt = "%s", newline = ',')

# Get a samples in the Queue
def _get_queue(unix_, save_local, save_real_time, display):
    try:
        data_ = q.get(True, timeout = 5)
        if save_local and not data_[-1]:
            _save_image(data_[0], unix_, path_temp)
        if save_real_time and not data_[-1]:
            _save_image(data_[0], unix_, path_queue)
        if display and not data_[-1]:
            x, y = _sun_position(data_[0], sun_pixels = 45000.)
            print('>> x_sun: {}  y_sun: {} Unix: {} Time: {} Name: {}'.format(x, y, data_[1], data_[2], unix_) )
            _save_data(x, y, unix_, name = 'IR', path = path_queue)
        return data_[-1]
    except:
        print('ERROR: Reading IR-Queue Error!')
        return True

def _init():
    cam_ = _open_camera()
    _ir_thread_flag = _start_threads(cam_)
    return cam_, _ir_thread_flag

def _kill(_ir_thread_flag, cam_):
    _kill_threads(_ir_thread_flag)
    _close_camera(cam_)

def _reset(_ir_thread_flag, cam_):
    print('>> Reset Infrared')
    execv(executable, ['python'] + argv)

def _main(save_local, save_real_time, display, min_elevation, freq):

    cam_, _ir_thread_flag = _init()

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
                    if flag:_reset(_ir_thread_flag, cam_)
                    diff = unix_ - time() + freq - 0.014
                    #print(unix_, flag, time(), diff)
            sleep(diff)
        except:
            break

    _kill(_ir_thread_flag, cam_)

def _setup(usb):
    system('sudo ykushcmd -d {}'.format(usb) )
    sleep(5.)
    system('sudo ykushcmd -u {}'.format(usb) )
    sleep(20.)

# Queue Initialization
q = Queue(BUFFER_SIZE)
PTR_PY_FRAME_CALLBACK = CFUNCTYPE(None, POINTER(uvc_frame), c_void_p)(py_frame_callback)

if __name__ == '__main__':
    _setup(usb = 2)
    _main(save_local = True, save_real_time = True, display = True, min_elevation = 15, freq = 15)
