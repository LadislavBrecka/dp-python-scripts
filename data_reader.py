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
    def __init__(self, u_speed, y_speed, w_pos, y_pos):
        self.u_speed = u_speed
        self.y_speed = y_speed
        self.w_pos = w_pos
        self.y_pos = y_pos


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

        self.data_u_speed = collections.deque([0] * plotLength, maxlen=plotLength)
        self.data_y_speed = collections.deque([0] * plotLength, maxlen=plotLength)
        self.data_w_pos = collections.deque([0] * plotLength, maxlen=plotLength)
        self.data_y_pos = collections.deque([0] * plotLength, maxlen=plotLength)
        self.abs_pos_ylim = (-1000, 1000)
        self.csvData = []

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
                      lines_u_speed, lineValueText_u_speed, lineLabel_u_speed, ax1,
                      lines_y_speed, lineValueText_y_speed, lineLabel_y_speed, ax2,
                      lines_w_pos, lineValueText_w_pos, lineLabel_w_pos, ax3,
                      lines_y_pos, lineValueText_y_pos, lineLabel_y_pos, ax4):

        currentTimer = time.perf_counter()
        # the first reading will be erroneous
        self.plotTimer = int((currentTimer - self.previousTimer) * 1000)
        self.previousTimer = currentTimer

        timeText.set_text('Plot Interval = ' + str(self.plotTimer) + 'ms')

        # we get the latest data point and append it to our array
        try:
            new_values = struct.unpack('<iiii', self.rawData)  # unpack the values
            parsed_data = UsartData(*new_values)
            print(parsed_data)
        except Exception:
            print(self.rawData)
            parsed_data = UsartData(self.data_u_speed[-1],
                                    self.data_y_speed[-1],
                                    self.data_w_pos[-1],
                                    self.data_y_pos[-1])

        self.data_u_speed.append(parsed_data.u_speed)
        self.data_y_speed.append(parsed_data.y_speed)
        self.data_w_pos.append(parsed_data.w_pos)
        self.data_y_pos.append(parsed_data.y_pos)

        lines_u_speed.set_data(range(self.plotMaxLength), self.data_u_speed)
        lines_y_speed.set_data(range(self.plotMaxLength), self.data_y_speed)
        lines_w_pos.set_data(range(self.plotMaxLength), self.data_w_pos)
        lines_y_pos.set_data(range(self.plotMaxLength), self.data_y_pos)

        lineValueText_u_speed.set_text('[' + lineLabel_u_speed + '] = ' + str(parsed_data.u_speed))
        lineValueText_y_speed.set_text('[' + lineLabel_y_speed + '] = ' + str(parsed_data.y_speed))
        lineValueText_w_pos.set_text('[' + lineLabel_w_pos + '] = ' + str(parsed_data.w_pos))
        lineValueText_y_pos.set_text('[' + lineLabel_y_pos + '] = ' + str(parsed_data.y_pos))

        # dynamically adjust ax3 if abs pos. overflow y limit
        if (abs(parsed_data.y_pos) > self.abs_pos_ylim[1] or abs(parsed_data.w_pos) > self.abs_pos_ylim[1]):
            self.abs_pos_ylim = (self.abs_pos_ylim[0] * 2, self.abs_pos_ylim[1] * 2)
            ax3.set_ylim(self.abs_pos_ylim[0], self.abs_pos_ylim[1])
            ax4.set_ylim(self.abs_pos_ylim[0], self.abs_pos_ylim[1])

        elif ((max(abs(min(self.data_y_pos)), abs(max(self.data_y_pos))) < self.abs_pos_ylim[1] / 2 and self.abs_pos_ylim[1] > 10000) or 
              (max(abs(min(self.data_w_pos)), abs(max(self.data_w_pos))) < self.abs_pos_ylim[1] / 2 and self.abs_pos_ylim[1] > 10000)):
            self.abs_pos_ylim = (self.abs_pos_ylim[0] / 2, self.abs_pos_ylim[1] / 2)
            ax3.set_ylim(self.abs_pos_ylim[0], self.abs_pos_ylim[1])
            ax4.set_ylim(self.abs_pos_ylim[0], self.abs_pos_ylim[1])

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
        df = pd.DataFrame([self.data_u_speed, self.data_y_speed, self.data_w_pos, self.data_y_pos])
        df.to_csv('/home/ladislav/Desktop/data.csv')


def main():
    portName = '/dev/ttyACM0'
    baudRate = 115200
    maxPlotLength = 1000
    dataNumBytes = 12
    # initializes all required variables
    s = serialPlot(portName, baudRate, maxPlotLength, dataNumBytes)
    # starts background thread
    s.readSerialStart()

    # plotting starts below
    pltInterval = 10    # Period at which the plot animation updates [ms]
    xmin = 0
    xmax = maxPlotLength
    fig, ax = plt.subplots(2, 2)
    ax1 = ax[0, 0]
    ax2 = ax[0, 1]
    ax3 = ax[1, 0]
    ax4 = ax[1, 1]
    timeText = ax1.text(-0.06, 1.2, '', transform=ax1.transAxes)

    # subplot 1 - Input
    (lines_u_speed, lineValueText_u_speed, lineLabel_u_speed) = configureSubplot(
        ax1, title='PWM % of input voltage', xlabel='Sample [k]', ylabel='Percentage [%]',
        lineLabel='PWM - u_speed', xlim=(xmin, xmax), ylim=(-100, 100))

    # subplot 2 - HAL 1 Sensor
    (lines_y_speed, lineValueText_y_speed, lineLabel_y_speed) = configureSubplot(
        ax2, title='Speed by HAL Sensor', xlabel='Sample [k]', ylabel='Frequency [Hz]',
        lineLabel='Speed - y_speed', xlim=(xmin, xmax), ylim=(-270, 270))

    # subplot 3 - Set Point value of position
    (lines_w_pos, lineValueText_w_pos, lineLabel_w_pos) = configureSubplot(
        ax3, title='Position Set Point', xlabel='Sample [k]', ylabel='Abs. pos [ticks]',
        lineLabel='Position - w_pos', xlim=(xmin, xmax), ylim=(-10000, 10000))
    
    # subplot 4 - HAL 1 absolute position
    (lines_y_pos, lineValueText_y_pos, lineLabel_y_pos) = configureSubplot(
        ax4, title='Position by HAL Sensor', xlabel='Sample [k]', ylabel='Abs. pos [ticks]',
        lineLabel='Position - y_pos', xlim=(xmin, xmax), ylim=(-10000, 10000))

    # animation plotting function
    anim = animation.FuncAnimation(fig, 
                                   s.updateGraphs, 
                                   fargs=(timeText,
                                          lines_u_speed, lineValueText_u_speed, lineLabel_u_speed, ax1,
                                          lines_y_speed, lineValueText_y_speed, lineLabel_y_speed, ax2,
                                          lines_w_pos, lineValueText_w_pos, lineLabel_w_pos, ax3,
                                          lines_y_pos, lineValueText_y_pos, lineLabel_y_pos, ax4),
                                   interval=pltInterval)

    ax1.legend(loc="upper left")
    ax2.legend(loc="upper left")
    ax3.legend(loc="upper left")
    ax4.legend(loc="upper left")

    # plt.tight_layout()
    plt.show()
    s.close()


def configureSubplot(ax, title, xlabel, ylabel, lineLabel, xlim, ylim):
    # ax.set_title(title)
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_xlim(xlim[0], xlim[1])
    ax.set_ylim(ylim[0], ylim[1])
    lines = ax.plot([], [], label=lineLabel)[0]
    lineValueText = ax.text(0.01, 0.65, '', transform=ax.transAxes)
    return (lines, lineValueText, lineLabel)


if __name__ == '__main__':
    main()
