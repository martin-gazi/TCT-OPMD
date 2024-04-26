from RsInstrument import *
import os
import pyvisa as visa
import matplotlib.pyplot as plt
import numpy as np
import time

class rhodeschwarz_rtp044():
   
    def __init__(self,default_channel=1):
        self.device = RsInstrument('GPIB1::20::INSTR', True, False)
        print(self.device.query('*IDN?'))
        self.default_channel=default_channel
        self.visa_timeout = 6000                # Timeout for VISA Read Operations
        self.opc_timeout = 3000                 # Timeout for opc-synchronised operations
        self.instrument_status_checking = True  # Error check after each command

    def convert_units(self,quantity,units):
        unit_symbol = units[0]
        if unit_symbol == 'G':
            quantity *= 10**9
        elif unit_symbol == 'M':
            quantity *= 10**6
        elif unit_symbol == 'k':
            quantity *= 10**3
        elif unit_symbol == 'm':
            quantity /= 10**3
        elif unit_symbol == 'u':
            quantity /= 10**6
        elif unit_symbol == 'n':
            quantity /= 10**9
        elif unit_symbol == 'p':
            quantity /= 10**12
        elif unit_symbol == 'f':
            quantity /= 10**15
        else:
            print('Unsupported units value, please use M, G, k, m, u, n, p, f or base units')
            exit()
        return quantity
    
    def take_data(self):
        self.device.write(':RUNSingle')

    def single(self):
        self.device.write(':SINGle')

    def run(self):
        self.device.write(':RUN')
        
    def stop(self):
        self.device.write(':STOP')
    
    def set_scale(self,scale,units='V',channel=None):
        if not channel:
            channel=self.default_channel
        if not units == 'V':
            scale = self.convert_units(scale,units)
        self.device.write(':CHANNEL'+str(channel)+':SCAL '+str(scale))
        return self.device.query(':CHANNEL'+str(channel)+':SCAL?')
   
    def get_scale(self,channel=None):
        if not channel:
            channel=self.default_channel
        return self.device.query(':CHANNEL'+str(channel)+':SCAL?')   # in Volts
		
    def get_range(self,channel=None):
        if not channel:
            channel=self.default_channel
        return float(self.device.query(':CHANNEL'+str(channel)+':RANGE?'))  # in Volts    

    def change_offset(self,delta,units='V',channel=None):
        if not channel:
            channel=self.default_channel
        current_offset=float(self.device.query(':CHANNEL'+str(channel)+':OFFSET?'))
        if not units == 'V':
            delta = self.convert_units(delta,units)
        self.device.write(':CHANNEL'+str(channel)+':OFFSET '+str(current_offset+delta))
	
    def set_offset(self,val,units='V',channel=None):
        if not channel:
            channel=self.default_channel
        if not units == 'V':
            val = self.convert_units(val,units)
        self.device.write(':CHANNEL'+str(channel)+':OFFSET '+str(val))
        
    def get_offset(self,channel=None):
        if not channel:
            channel=self.default_channel
        return float(self.device.query(':CHANNEL'+str(channel)+':OFFS?'))   # in Volts
 
    def set_timescale(self,value,units='s'):
        if not units == 's':
            value = self.convert_units(value,units)
        self.device.write_str(':TIM:SCAL '+str(value))
 
    def get_timescale(self):
        return float(self.device.query(':TIM:SCAL?'))

    def set_timedelay(self,delay,units='s'):
        if not units == 's':
            delay = self.convert_units(delay,units)
        self.device.write(':TIM:HOR:POS '+str(delay))
        
    def get_timedelay(self):
        return float(self.device.query(':TIM:HOR:POS?'))

    def check_channel_state(self,channel=None):
        if not channel:
            print('No channel specified for state check')
        else:
            return self.device.query('CHANnel'+str(channel)+':STATe?')

    def turn_channel_on(self,channel=None):
        if not channel:
            print('No channel specified to be turned on')
        else:
            self.device.write(':CHANnel'+str(channel)+' ON')

    def turn_channel_off(self,channel=None):
        if not channel:
            print('No channel specified to be turned off')
        else:
            self.device.write(':CHANnel'+str(channel)+' OFF')  

    def set_filter_value(self,channel=None,value=None,units='Hz'):
        if not channel:
            channel=self.default_channel
        if not value:
            print('No value for digital filter of channel '+str(channel)+' defined!')
        else:
            if not units == 'Hz':
                value = self.convert_units(value,units)
            value = int(value)
            self.device.write(':CHANnel'+str(channel)+':DIGFilter:CUToff '+str(value))          

    def turn_filter_on(self,channel=None,value=None,units='Hz'):
        if not channel:
            channel=self.default_channel
        if not value==None:
            self.set_filter_value(channel,value,units)
        self.device.write(':CHANnel'+str(channel)+':DIGFilter:STATe ON')

    def turn_filter_off(self,channel=None):
        if not channel:
            channel=self.default_channel
        self.device.write(':CHANnel'+str(channel)+':DIGFilter:STATe OFF')

    def report_channel_state(self,channel=None):
        if not channel:
            channel=self.default_channel
        rs_scale = self.get_scale()
        rs_offset = self.get_offset()
        print(f'Channel {channel} set to {rs_scale} V per division with offset {rs_offset} V')

    def report_timebase_state(self,channel=None):
        rs_timescale = self.get_timescale()
        rs_timedelay = self.get_timedelay()
        print(f'Timescale set to {rs_timescale} s per division with offser {rs_timedelay} s') 

    def read_waveform(self,channel=None):
        if not channel:
            channel=self.default_channel
        self.device.write('FORM:DATA ASC,0')
        all_data = self.device.query(':CHANnel'+str(channel)+':WAVeform:DATA?').split(',')
        data = [float(x) for x in all_data]
        return data

    def read_timebase(self):
        time_range = float(self.device.query(':TIM:RANGe?'))
        time_delay = self.get_timedelay()
        base_start = -time_range/2 + time_delay
        base_end = +time_range/2 + time_delay
        base_res = float(self.device.query(':ACQ:RES?'))
        base = list(np.arange(base_start,base_end,base_res))
        return base

    def plot_waveform(self,channel=None):
        if not channel:
            channel=self.default_channel
        self.take_data()
        timebase = self.read_timebase()
        result = self.read_waveform(channel)
        plt.plot(timebase, result)
        plt.show()
        
    def plot_all_active(self):
        self.take_data()
        channel_colours = ['yellow', 'green', 'orange', 'blue']
        timebase = self.read_timebase()
        plt.figure(1)
        for i in range(1,5):
            if self.check_channel_state(channel=i)=='1':
                data = self.read_waveform(channel=i)
                plt.plot(timebase, data, color=channel_colours[i-1])
        plt.show()

    def screen_on(self):
        self.device.write("SYST:DISP:UPD ON")                   # Turn display on

    def save_screenshot(self,path=None,name=None,trig=False):
        if not path:
            path = 'c:\RS Screenshots'
        if not name:
            file_name = 'RTP_Screenshot_'+str(time.time_ns())+'.png'
        else:
            file_name = str(name)+'.png'
        file_path_instr = 'C:\Temp\Temp_Screenshot.png'
        file_path_pc = str(path)+'\\'+str(file_name)

        if trig==True:
            self.take_data()
        self.device.write("SYST:DISP:UPD ON")                   # Turn display on
        self.device.write("HCOP:DEST 'MMEM'")                   # Set file to be saved to memory
        self.device.write("HCOP:DEV:LANG PNG")                  # Set file format
        self.device.write("HCOP:DEV:INV OFF")                   # Colour inversion off
        self.device.query("*OPC?")
        self.device.write("MMEM:NAME '"+file_path_instr+"'")    # Define path to saved file
        self.device.write("HCOP:IMM")                           # Save file
        self.device.read_file_from_instrument_to_pc(file_path_instr, file_path_pc)

### Dev section - following definitons in trial period
### ---------------------------------------------------------------------------

# At this point the group is defined as 4. Should generalize later
    def clear_meas(self,group=1):
        self.device.write(":MEASurement"+str(group)+":CLEar")

    def run_meas(self,group=1,count=1000):
        self.device.write(":MEASurement"+str(group)+":CLEar")
        self.device.write(":MEASurement"+str(group)+":LTMeas:COUNt "+str(count))
        self.device.write(":MEASurement"+str(group)+":LTMeas:STATe ON")

# Need to check that the group meas is enabled, becuase otherwise it fails/freezes
    def get_meas(self,group=1):
        self.device.write(":MEASurement"+str(group)+":STATistics:ENABle 1")
        meas = self.device.query(":MEASurement"+str(group)+":RESult:AVG?")
        return meas

    def get_meas_std(self,group=1):
        self.device.write(":MEASurement"+str(group)+":STATistics:ENABle 1")
        meas_std = self.device.query(":MEASurement"+str(group)+":RESult:STDDev?")
        return meas_std

    def get_meas_count(self,group=1):
        self.device.write(":MEASurement"+str(group)+":STATistics:ENABle 1")
        meas_count = self.device.query(":MEASurement"+str(group)+":RESult:EVTCount?")
        return meas_count

### ---------------------------------------------------------------------------

def quick_acquire(samples=10):
    rs.run()
    data = np.array(rs.read_timebase())[:-1]
    for i in range(0,samples):
        values = rs.read_waveform(channel=2)
        values = np.array(values)
        data = np.vstack([data, values])
        #rs.single()
    #data = np.transpose(data)
    #np.savetxt('LGAD_array_240V_gate830mv_bias90mA_20C.csv', data, delimiter=',', fmt='%.7g')
    return data
        

if __name__=='__main__':
    rs=rhodeschwarz_rtp044()
    # rs.set_scale(scale=100, units='mV')
    # rs.set_offset(val=0, units='mV')
    # rs.set_timescale(value=1, units='ns')
    # rs.set_timedelay(delay=3, units='ns') 
    rs.report_channel_state()
    rs.report_timebase_state()
