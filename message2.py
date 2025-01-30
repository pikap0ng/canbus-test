import can # type: ignore
import struct
from enum import Enum

class Bms(Enum):
    VOLTAGE_IN_RANGE = 1
    LOW_CELL_VOLTAGE = 2

# baudrate = 2500000
# port = '/dev/ttyUSB0'

can_interface = 'can0'
# bus = can.interface.Bus(can_interface, bustype='socketcan', bitrate=250000)
bus = can.interface.Bus('can0', bustype='socketcan', bitrate=250000)

def decode(m_id, m_bytes):
    if (m_id) == 0x101:
        temp_avg, temp_low, null = struct.unpack('<HHb', m_bytes[:5])
        high_cell_v, = struct.unpack('>H', m_bytes[-2:])
        #print('Avg temp: {:.1f} C\t Low temp: {:.1f} C\t Highest Voltage: {:.2f} V'.format(temp_avg,temp_low,high_cell_v*0.0001))
        return (temp_avg, temp_low, high_cell_v)
    
    elif (m_id) == 0x100:
        pack_current, null, null, temp_high = struct.unpack('>Hbbb', m_bytes[:5])
        pack_voltage, = struct.unpack('<H', m_bytes[2:4])
        dtc_flags, = struct.unpack('<H', m_bytes[-2:])
        #print('Pack current: {:.2f} A\t Pack Voltage: {:.2f}V\t High Temp: {:.1f}C\t dtc flags: {}'.format(pack_current*0.1,pack_voltage*0.1,temp_high,dtc_flags))
        return (pack_current, temp_high, pack_voltage, dtc_flags)
    
    elif (m_id) == 0x103:
        cell_id, m_bytes = m_bytes[0], m_bytes[1:]
        cell_id = cell_id + 1
        instant_voltage, internal_resistance, open_voltage = struct.unpack('>HHH', m_bytes)
        #print('Cell: {:2.0f}\t Voltage: {:.2f} mV\t Resistance: {:.2f} mOhm\t Open Volts: {:.2f} mV'.format(cell_id,instant_voltage*0.1,internal_resistance*0.01,open_voltage*0.1))            
        # print('Cell: {:2.0f}\t Voltage: {:.2f} mV'.format(cell_id,instant_voltage*0.1))
        return (cell_id, instant_voltage, internal_resistance, open_voltage)

def read_bms():
    cells = [0] * 12
    output = {
        "temp_avg": "",
        "temp_low": "",
        "temp_high": "",
        "highest_cell_voltage": "",
        "pack_voltage": "",
        "pack_current": "",
        "dtc_flags": "",
        #diag trouble code -- if nonzero stop pod
        "cells": ""
    }
    
    while 0 in cells:
        try:
            # Message format
            # tIIILDDDDDDDDTTTT
            # III = CAN ID
            # L = Message Length
            # D = Message data
            # T = Timestamp
            message = bus.recv(timeout=1.0)  # Wait up to 1 second for a message
            if message is None:
                continue
            
            m_id = message.arbitration_id
            m_bytes = message.data

            data = decode(m_id, m_bytes)
            if m_id == 0x103:
                cells[data[0] - 1] = data
            elif m_id == 0x100:
                output["temp_high"] = data[1]
                output["pack_voltage"] = data[2]
                output["pack_current"] = data[0]
                output["dtc_flags"] = data[3]
            elif m_id == 0x101:
                output["temp_avg"] = data[0]
                output["temp_low"] = data[1]
                output["highest_cell_voltage"] = data[2]
        except Exception as e:
            print(f"Error reading CAN message: {e}")
    
    output["cells"] = cells
    return output

def low_voltage_check():
    low_voltage = False
    while not low_voltage:
        output = read_bms()
        for n in range(12):
            volt = output["cells"][n][1] * 0.1
            cell = output["cells"][n][0]
            if volt <= 3400:
                print(f"ERROR {Bms(2).name}")
                print(f'Cell: {cell:2.0f}\t Voltage: {volt:.2f} mV')
                low_voltage = True
                break
            else:
                print(f'Cell: {cell:2.0f}\t Voltage: {volt:.2f} mV')

# start voltage check
low_voltage_check()
