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

class UsartData:
    def __init(self, sp, speed, absolute_position):
        self.sp = sp
        self.speed = speed
        self.absolute_position = absolute_position


class serialPlot:
    def __init__(self, serialPort='/dev/ttyACM0', serialBaud=115200, plotLength=100, dataNumBytes=2):
        self.port = serialPort
        self.baud = serialBaud
        self.plotMaxLength = plotLength
        self.dataNumBytes = dataNumBytes
        self.rawData = bytearray(dataNumBytes)
        self.isRun = True
        self.isReceiving = False
        self.thread = None
        self.plotTimer = 0
        self.previousTimer = 0

        self.data_sp = collections.deque([0] * plotLength, maxlen=plotLength)
        self.data_hal1 = collections.deque([0] * plotLength, maxlen=plotLength)
        self.data_hal2 = collections.deque([0] * plotLength, maxlen=plotLength)
        # self.csvData = []

        print('Trying to connect to: ' + str(serialPort) +
              ' at ' + str(serialBaud) + ' BAUD.')
        try:
            self.serialConnection = serial.Serial(
                serialPort, serialBaud, timeout=4)
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

    def getSerialData(self, frame, timeText,
                      lines_sp, lineValueText_sp, lineLabel_sp,
                      lines_hal1, lineValueText_hal1, lineLabel_hal1,
                      lines_hal2, lineValueText_hal2, lineLabel_hal2):

        currentTimer = time.perf_counter()
        # the first reading will be erroneous
        self.plotTimer = int((currentTimer - self.previousTimer) * 1000)
        self.previousTimer = currentTimer

        timeText.set_text('Plot Interval = ' + str(self.plotTimer) + 'ms')

        # we get the latest data point and append it to our array
        (value_sp, value_hal1, value_hal2) = self.parseRawData()

        # self.data_sp.append(value_sp)
        # self.data_hal1.append(value_hal1)
        # self.data_hal2.append(value_hal2)

        # lines_sp.set_data(range(self.plotMaxLength), self.data_sp)
        # lines_hal1.set_data(range(self.plotMaxLength), self.data_hal1)
        # lines_hal2.set_data(range(self.plotMaxLength), self.data_hal2)

        # lineValueText_sp.set_text('[' + lineLabel_sp + '] = ' + str(value_sp))
        # lineValueText_hal1.set_text('[' + lineLabel_hal1 + '] = ' + str(value_hal1))
        # lineValueText_hal2.set_text('[' + lineLabel_hal2 + '] = ' + str(value_hal2))
        # self.csvData.append(self.data[-1])

    def parseRawData(self):
        print("aa")
        try:
            raw_value = self.rawData.decode()
            print(raw_value)
            # raw_values_splited = raw_value.rsplit('-', 2)
            # print(raw_values_splited)
            # value_sp = int("".join(filter(str.isdigit, raw_values_splited[0])))
            # value_hal1 = int("".join(filter(str.isdigit, raw_values_splited[1])))
            # value_hal2 = int("".join(filter(str.isdigit, raw_values_splited[2])))
            # print(value_sp, value_hal1, value_hal2)
            # return (value_sp, value_hal1, value_hal2)
            IndexError
        except Exception:
            return (self.data_sp[-1], self.data_hal1[-1], self.data_hal2[-1])

    def backgroundThread(self):    # retrieve data
        time.sleep(1.0)  # give some buffer time for retrieving data
        self.serialConnection.reset_input_buffer()
        while (self.isRun):
            self.rawData = self.serialConnection.readline()
            self.isReceiving = True

    def close(self):
        self.isRun = False
        self.thread.join()
        self.serialConnection.close()
        print('Disconnected...')
        # df = pd.DataFrame(self.csvData)
        # df.to_csv('/home/rikisenia/Desktop/data.csv')


def main():
    portName = '/dev/ttyACM0'
    baudRate = 115200
    maxPlotLength = 1000
    # number of bytes of 1 data point (integer has 4 bytes)
    dataNumBytes = 8
    # initializes all required variables
    s = serialPlot(portName, baudRate, maxPlotLength, dataNumBytes)
    # starts background thread
    s.readSerialStart()

    # plotting starts below
    pltInterval = 50    # Period at which the plot animation updates [ms]
    xmin = 0
    xmax = maxPlotLength
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1)
    timeText = ax1.text(-0.06, 1.2, '', transform=ax1.transAxes)

    # subplot 1 - Input
    lineLabel_sp = 'Percentage of input PWM signal'
    (lines_sp, lineValueText_sp, lineLabel_sp) = configureSubplot(
        ax1, title='PWM % of input voltage - Set point', xlabel='Sample [k]', ylabel='Percentage [%]',
        lineLabel=lineLabel_sp, xlim=(xmin, xmax), ylim=(0, 100))

    # subplot 2 - HAL 1 Sensor
    (lines_hal1, lineValueText_hal1, lineLabel_hal1) = configureSubplot(
        ax2, title='HAL Sensor 2 data read', xlabel='Sample [k]', ylabel='Frequency [Hz]',
        lineLabel='Frequency of HAL 1 signal', xlim=(xmin, xmax), ylim=(0, 350))

    # subplot 3 - HAL 2 Sensor
    (lines_hal2, lineValueText_hal2, lineLabel_hal2) = configureSubplot(
        ax3, title='HAL Sensor 2 data read', xlabel='Sample [k]', ylabel='Frequency [Hz]',
        lineLabel='Frequency of HAL 2 signal', xlim=(xmin, xmax), ylim=(0, 350))

    # animation plotting function
    anim = animation.FuncAnimation(fig, 
                                   s.getSerialData, 
                                   fargs=(timeText,
                                          lines_sp, lineValueText_sp, lineLabel_sp,
                                          lines_hal1, lineValueText_hal1, lineLabel_hal1,
                                          lines_hal2, lineValueText_hal2, lineLabel_hal2),
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
