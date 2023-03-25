import serial

from read_utils import ReadLine

ser = serial.Serial('/dev/ttyACM0', 115200)
rl = ReadLine(ser)

while True:
    raw_data = rl.readline().decode()
    freq = raw_data[raw_data.find('=')+1 : raw_data.find('H')]
    print(freq)