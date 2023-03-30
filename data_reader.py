#!/usr/bin/env python

from threading import Thread
import serial
import time
import collections
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import struct
import pandas as pd
import re
import sys
from itertools import repeat

class UsartData:
    def __init__(self, sp, speed, abs_pos):
        self.sp = sp
        self.speed = speed
        self.abs_pos = abs_pos


class serialPlot:
    def __init__(self, serialPort='/dev/ttyACM0', serialBaud=115200, plotLength=100, dataNumBytes=2):
        self.port = serialPort
        self.baud = serialBaud
        self.plotMaxLength = plotLength
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0
        self.dataNumBytes = dataNumBytes
        self.rawData = bytes

        self.data_sp = collections.deque([0] * plotLength, maxlen=plotLength)
        self.data_speed = collections.deque([0] * plotLength, maxlen=plotLength)
        self.data_abs_pos = collections.deque([0] * plotLength, maxlen=plotLength)
        self.abs_pos_ylim = (-10000, 10000)
        # self.csvData = []

        print('Trying to connect to: ' + str(serialPort) +
              ' at ' + str(serialBaud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(
                serialPort, serialBaud, timeout=500)
            print('Connected to ' + str(serialPort) +
                  ' at ' + str(serialBaud) + ' BAUD.')
        except:
            print("Failed to connect with " + str(serialPort) +
                  ' at ' + str(serialBaud) + ' BAUD.')

    def readSerialStart(self):
        if self.thread == None:
            self.thread = Thread(target=self.backgroundThread)
            self.thread.start()
            # Block till we start receiving values
            while self.isReceiving != True:
                time.sleep(0.1)

    def updateGraphs(self, frame, timeText,
                      lines_sp, lineValueText_sp, lineLabel_sp, ax1,
                      lines_speed, lineValueText_speed, lineLabel_speed, ax2,
                      lines_abs_pos, lineValueText_abs_pos, lineLabel_abs_pos, ax3):

        currentTimer = time.perf_counter()
        # the first reading will be erroneous
        self.plotTimer = int((currentTimer - self.previousTimer) * 1000)
        self.previousTimer = currentTimer

        timeText.set_text('Plot Interval = ' + str(self.plotTimer) + 'ms')

        # we get the latest data point and append it to our array
        try:
            new_values = struct.unpack('<iii', self.rawData)  # unpack the values
            parsed_data = UsartData(*new_values)
            print(parsed_data)
        except Exception:
            print(self.rawData)
            parsed_data = UsartData(self.data_sp[-1],
                                    self.data_speed[-1],
                                    self.data_abs_pos[-1])

        self.data_sp.append(parsed_data.sp)
        self.data_speed.append(parsed_data.speed)
        self.data_abs_pos.append(parsed_data.abs_pos)

        lines_sp.set_data(range(self.plotMaxLength), self.data_sp)
        lines_speed.set_data(range(self.plotMaxLength), self.data_speed)
        lines_abs_pos.set_data(range(self.plotMaxLength), self.data_abs_pos)

        lineValueText_sp.set_text('[' + lineLabel_sp + '] = ' + str(parsed_data.sp))
        lineValueText_speed.set_text('[' + lineLabel_speed + '] = ' + str(parsed_data.speed))
        lineValueText_abs_pos.set_text('[' + lineLabel_abs_pos + '] = ' + str(parsed_data.abs_pos))

        # dynamically adjust axes 3 if abs pos. overflow y limit
        if (abs(parsed_data.abs_pos) > self.abs_pos_ylim[1]):
            self.abs_pos_ylim = (self.abs_pos_ylim[0] * 2, self.abs_pos_ylim[1] * 2)
            ax3.set_ylim(self.abs_pos_ylim[0], self.abs_pos_ylim[1])
        elif (max(abs(min(self.data_abs_pos)), abs(max(self.data_abs_pos))) < self.abs_pos_ylim[1] / 2 and self.abs_pos_ylim[1] > 10000):
            self.abs_pos_ylim = (self.abs_pos_ylim[0] / 2, self.abs_pos_ylim[1] / 2)
            ax3.set_ylim(self.abs_pos_ylim[0], self.abs_pos_ylim[1])

        # self.csvData.append(self.data[-1])

    def backgroundThread(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while (self.isRun):
            start_byte = self.serialConnection.read(1)   # read start byte
            if start_byte == b'S':                       # check if it's S
                data = self.serialConnection.read_until(b'Z')   # read until stop byte 'Z'
                self.rawData = data[1:len(data)-1]                # trim the bytes to contain only message
            self.isReceiving = True

    def close(self):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')
        df = pd.DataFrame([self.data_sp, self.data_speed])
        df.to_csv('/home/ladislav/Desktop/data.csv')


def main():
    portName = '/dev/ttyACM0'
    baudRate = 115200
    maxPlotLength = 3000
    dataNumBytes = 12
    # initializes all required variables
    s = serialPlot(portName, baudRate, maxPlotLength, dataNumBytes)
    # starts background thread
    s.readSerialStart()

    # plotting starts below
    pltInterval = 10    # Period at which the plot animation updates [ms]
    xmin = 0
    xmax = maxPlotLength
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1)
    timeText = ax1.text(-0.06, 1.2, '', transform=ax1.transAxes)

    # subplot 1 - Input
    lineLabel_sp = 'Percentage of input PWM signal'
    (lines_sp, lineValueText_sp, lineLabel_sp) = configureSubplot(
        ax1, title='PWM % of input voltage - Set point', xlabel='Sample [k]', ylabel='Percentage [%]',
        lineLabel=lineLabel_sp, xlim=(xmin, xmax), ylim=(-100, 100))

    # subplot 2 - HAL 1 Sensor
    (lines_speed, lineValueText_speed, lineLabel_speed) = configureSubplot(
        ax2, title='Speed by HAL Sensor', xlabel='Sample [k]', ylabel='Frequency [Hz]',
        lineLabel='Speed', xlim=(xmin, xmax), ylim=(-350, 350))

    # subplot 3 - HAL 2 Sensor
    (lines_abs_pos, lineValueText_abs_pos, lineLabel_abs_pos) = configureSubplot(
        ax3, title='Absolute position by HAL Sensor', xlabel='Sample [k]', ylabel='Abs. pos [ticks]',
        lineLabel='Absolute position', xlim=(xmin, xmax), ylim=(-10000, 10000))

    # animation plotting function
    anim = animation.FuncAnimation(fig, 
                                   s.updateGraphs, 
                                   fargs=(timeText,
                                          lines_sp, lineValueText_sp, lineLabel_sp, ax1,
                                          lines_speed, lineValueText_speed, lineLabel_speed, ax2,
                                          lines_abs_pos, lineValueText_abs_pos, lineLabel_abs_pos, ax3),
                                   interval=pltInterval)

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper left")
    ax3.legend(loc="upper left")

    plt.tight_layout()
    plt.show()
    s.close()


def configureSubplot(ax, title, xlabel, ylabel, lineLabel, xlim, ylim):
    ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(xlim[0], xlim[1])
    ax.set_ylim(ylim[0], ylim[1])
    lines = ax.plot([], [], label=lineLabel)[0]
    lineValueText = ax.text(0.01, 0.65, '', transform=ax.transAxes)
    return (lines, lineValueText, lineLabel)


if __name__ == '__main__':
    main()
