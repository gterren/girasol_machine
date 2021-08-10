# To do list:
# - Select Only the Necessary Comlumns
# - Transform time to unix times
# - Transform temperature in F. to celsius
# - Interpolar the data that is missing to 1 second resoluction
# - Check if any day in the girasol machine is not download yet
# - Either download it or remove them
# - Get Starting and ending data of the recording 2017_12_07-2019_01_18
# - Set code in functions
# - Make it rebust so it does not break in case of no existing data for a day
# - Lunch processing for all data

import csv
import requests
import time
import datetime

import numpy as np
import matplotlib.pylab as plt

from scipy import interpolate
from sys import argv
from os import system

# SAVES IMAGES IN THE FOLLOWING PATH
path_temp   = '/home/girasol/girasol_project/temp/'
path_source = '/home/girasol/girasol_project/source/'
path_queue  = '/home/girasol/girasol_project/real_time_queue/'

# Define the url to request data from
def _get_url(weather_station_id, day, month, year):
    url = r'https://www.wunderground.com/weatherstation/WXDailyHistory.asp?ID={}&day={}&month={}&year={}&graphspan=day&format=1'
    return url.format(weather_station_id, day, month, year)

# Request content on the url
def _request_page_data(url):
    page = requests.get(url)
    return page.content.decode("utf-8")

# Slip up data by rows
def _data_2_rows(data_):
    rows_ = []
    i = 0
    while True:
        ii = data_[i:].find(r'<br>')
        rows_.append(data_[i:i + ii])
        i = i + ii + 4
        if i > len(data_):
            break
    return rows_
# Temperature in F. to Celcius
def _celsius_2_fahrenheit(Temp):
    return (float(Temp) - 32.) * (5. / 9.)
# Presure in In. to mm.
def _inches_2_milimeters(In):
    return float(In) * 25.4
# Degrees to radinas
def _degrees_2_radias(Degree):
    return np.radians(float(Degree))
# Wind velocity in MPH to KPH
def _MPH_2_mps(MPH):
    return 1000. * float(MPH) * 1.609344 / 3600.
def to_seconds(date):
    return time.mktime(date.timetuple())
# Format columns to SI units and save it in a csv file
def _format_data(path, rows_, year, month, day):
    file_name = '{:04}_{:02}_{:02}.csv'.format(year, month, day)
    path = r'{}/{}'.format(path, file_name)
    idx_ = [0, 1, 2, 3, 5, 6, 8]
    with open(path, 'wb') as csv_file:
        writer = csv.writer(csv_file, delimiter = ',')
        for i in range(len(rows_) - 1):
            cells_ = rows_[i].split(',')
            cells_ = [cells_[idx] for idx in idx_]
            for ii in range(len(cells_)):
                # Return End of the line /n in string
                cells_[ii] = cells_[ii].lstrip()
                # Human Time to Unix
                if ii == 0 and i > 0.: cells_[ii] = to_seconds(datetime.datetime.strptime(cells_[ii], '%Y-%m-%d %H:%M:%S'))
                # Temperature in F. to Celcius
                if ii == 1 and i > 0.: cells_[ii] = _celsius_2_fahrenheit(cells_[ii])
                # Dew Point in F. to Celcius
                if ii == 2 and i > 0.: cells_[ii] = _celsius_2_fahrenheit(cells_[ii])
                # Presure in In. to mm.
                if ii == 3 and i > 0.: cells_[ii] = _inches_2_milimeters(cells_[ii])
                # Degrees to radinas
                if ii == 4 and i > 0.: cells_[ii] = _degrees_2_radias(cells_[ii])
                # Wind velocity in MPH to KPH
                if ii == 5 and i > 0.: cells_[ii] = _MPH_2_mps(cells_[ii])
            if i > 0.: writer.writerow(cells_)
    return path

weather_station_id = r'KNMALBUQ11'  # West UNM Central Campus
weather_station_id = r'KNMALBUQ473' # UNM Hospital Helipad
#weather_station_id = r'KNMALBUQ118' # Airport Weather Station

year  = int(argv[1])
month = int(argv[2])
day   = int(argv[3])
print(weather_station_id, year, month, day)

url = _get_url(weather_station_id, day, month, year)
print(url)
data_ = _request_page_data(url)
rows_ = _data_2_rows(data_)
path = _format_data(path_temp, rows_, year, month, day)
print(path)
