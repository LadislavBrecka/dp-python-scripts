import serial
import struct
import pandas as pd

class UsartData:
    def __init__(self, u_speed, y_speed, w_pos, y_pos):
        self.u_speed = u_speed
        self.y_speed = y_speed
        self.w_pos = w_pos
        self.y_pos = y_pos


def main():
    serial_connection = serial.Serial('/dev/ttyACM0', 115200)
    usart_data = []

    file_name = input("Type filename to start scanning serial port to pandas Dataframe.\nFilename: ")
    prev_parsed_data = UsartData(0, 0, 0, 0)

    try:
        while True:
            start_byte = serial_connection.read(1)                  # read start byte
            if start_byte == b'S':                                  # check if it's S
                data = serial_connection.read_until(b'Z')           # read until stop byte 'Z'
                rawData = data[1:len(data)-1]                       # trim the bytes to contain only message
                try:
                    new_values = struct.unpack('<iiii', rawData)
                    parsed_data = UsartData(*new_values)
                except Exception:
                    print("BLYAT")
                    parsed_data = prev_parsed_data

                
                print(parsed_data.u_speed)
                usart_data.append([parsed_data.u_speed, parsed_data.y_speed, parsed_data.w_pos, parsed_data.y_pos])
                prev_parsed_data = parsed_data

    except KeyboardInterrupt:
        print('You pressed ctrl+c')
        df = pd.DataFrame(usart_data)
        df.to_csv('/home/ladislav/Desktop/{}'.format(file_name))
        print("Dataset saved to file ", file_name)


if __name__ == '__main__':
    main()