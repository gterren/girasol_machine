import threading, subprocess

from sys import argv
from time import sleep
from os import popen, system, getcwd

# System PAHTS
#path_temp  = '/home/girasol/girasol_project/temp/'
#path_data  = '/home/girasol/girasol_project/data/'
path_codes = '/home/girasol/girasol_project/source/'

usb_1_name = 'ARC'
usb_2_name = 'Cubeternet'
usb_3_name = 'dog'

usb_names_   = [usb_1_name, usb_2_name, usb_3_name]
usb_numbers_ = [1, 2, 3]
code_names_  = ['thread_tracker.py', 'thread_visible.py', 'thread_infrared.py', 'thread_pyranometer.py']

def _start_screens(dev = None):
    def __start_screen(code_name):
        python_cmd = 'sudo python -W ignore {}/{}'.format(path_codes, code_name)
        screen_cmd = 'screen -S {} -dm {}'.format(code_name[7:-3], python_cmd)
        print(screen_cmd)
        _p_1 = subprocess.Popen(screen_cmd, stdout = subprocess.PIPE, shell = True)
        sleep(1.)
    if dev == None:
        for code_name in code_names_:
            __start_screen(code_name)
    else:
        __start_screen(code_names_[dev])

def _switch_on_usbs():
    system('sudo ykushcmd -u 1')
    system('sudo ykushcmd -u 2')
    system('sudo ykushcmd -u 3')
    sleep(25)

def _switch_off_usbs():
    system('sudo ykushcmd -d 1')
    system('sudo ykushcmd -d 2')
    system('sudo ykushcmd -d 3')

def _detect_usbs(dev = None):
    def __dectect_usb(usb_name):
        if usb_name in popen('lsusb').read():
            print('>> {} is connected'.format(usb_name))
            flag = False
        else:
            print('>> {} is not connected'.format(usb_name))
            flag = True
        return flag
    flag = False
    if dev == None or dev > 0:
        _switch_on_usbs()
        if dev == None:
            for usb_name in usb_names_:
                flag = __dectect_usb(usb_name)
                if flag: return flag
        else:
            flag = __dectect_usb(usb_names_[dev - 1])
    return flag

def _stop_screens(dev = None):
    def __stop_screen(code_name):
        system('sudo screen -X -S {} quit'.format(code_name[7:-3]) )
        print('>> Session stops: {}'.format(code_name[7:-3]))
        sleep(1.)

    if dev is None:
        for code_name in code_names_:
            __stop_screen(code_name)
    else:
        __stop_screen(code_names_[dev])

if __name__ == '__main__':
    if argv[1] == '0' and len(argv) == 2:
        _stop_screens()
    if argv[1] == '1' and len(argv) == 2:
        flag = _detect_usbs()
        if not flag:
            _start_screens()

    if argv[1] == '0' and len(argv) == 3:
        dev = int(argv[2])
        _stop_screens(dev)
    if argv[1] == '1' and len(argv) == 3:
        dev  = int(argv[2])
        flag = _detect_usbs(dev)
        if not flag:
            _start_screens(dev)
