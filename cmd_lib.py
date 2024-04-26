import sys,traceback,time,random,os,shutil,datetime
import numpy as np
import matplotlib.pyplot as plt

from Keithley_control import keithley_2410
from RTP044_oscilloscope import rhodeschwarz_rtp044
from QD_Laser_control import QD_Laser
from motion_stage_driver import MotionStageController   # XX May have problem when disconnected

### ------------------------------------------------------------------------------------

### Ramps the Keithley voltage to a target in steps of 20 V. Tagert must be negative (or is made so)
### Override allows positive voltages to be selected
def ramp_voltage(k, target_voltage, override=False):
    if target_voltage is None:
        target_voltage = k.get_voltage()
    elif target_voltage > 0 and override==False:        # Without override, only negative voltages supported
        print('Only non-positive target voltages allowed. Correct your value or set override=True')
        target_voltage = -target_voltage                # Changes target to negative voltage
    init_voltage = k.get_voltage()
    voltage_diff = target_voltage - init_voltage
    if voltage_diff == 0:
        msg = r'Voltage kept at {}V'.format(init_voltage)
        print(msg)
    else:
        volt_step = 20
        step_sign = int(abs(voltage_diff)/voltage_diff)
        steps = 1
        current_voltage = k.get_voltage()
        while abs(current_voltage-target_voltage) > volt_step:
            k.set_voltage(current_voltage + step_sign*volt_step)
            # XX Compliance check would be advantageous
            time.sleep(1)
            current_voltage = k.get_voltage()
            steps += 1
        k.set_voltage(target_voltage)
        current_voltage = k.get_voltage()
        msg = r'Voltage changed from {}V to {}V over {} steps'.format(init_voltage, current_voltage, steps)
        print(msg)
    return msg

## Autoscales the oscilloscope yaxis
def autoscale(osc,depth=0):
    if depth>30:
        print(r'Cannot set scale after {} steps'.format(depth))
        return False
    min_size = 4        # Minimum number of divisions taken by the signal amplitude
    max_size = 6        # Maximum number of divisions taken by the signal amplitude
    min_scale = 0.015   # Set minimum allowed scale (in V)
    upscale = 5         # Change scale such that the signal is 'upscale' times larger
    downscale = 1.5     # Change scale such that the signal is 'downscale' times smaller
    base_pos = 3        # Number of divisons the base is shifted downwards from the centre (set <5)
                        # Watch out! max_size - base_pos < 5 Otherwise the amplitude will not fit 
    
    current_scale = float(osc.get_scale(channel=2))
    osc.set_offset(val=3*current_scale,channel=2)       # Fixes the base, suitable for unipolar signal
    
    sample_wfs = 10     # Sample size of average waveform used for scaling
    data = np.array(osc.read_waveform(channel=2))
    for wave_no in range(sample_wfs-1):
        osc.run()
        waveform = np.array(osc.read_waveform(channel=2))
        data = np.vstack((data, waveform))
    data = np.mean(np.array(data),axis=0)
    amp = (np.max(data)-np.min(data))
    
    if amp < min_size*current_scale:
        if current_scale <= min_scale:
            osc.set_scale(min_scale, channel = 2)
            smallest_scale_reached = True
            msg = r'Scale limit rached at {}V in {} steps'.format(current_scale, depth)
            print(msg)
            return msg
        else:
            new_scale = max(round(amp/upscale, 3),min_scale)  # Max to give opportunity to stop at min scale
            osc.set_scale(new_scale, channel = 2)
            return autoscale(osc,depth=depth+1)
    elif amp > max_size*current_scale:
        new_scale = round(current_scale*downscale, 3)
        osc.set_scale(new_scale, channel = 2)
        return autoscale(osc,depth=depth+1)
    else:
        if (depth==0):
            msg = r'Scale kept at {}V'.format(current_scale)
            print(msg)
        else:
            msg = r'Scale changed to {}V in {} steps'.format(current_scale, depth)
            print(msg)
        return msg

def wave_acquire(osc,samples=10):
    osc.run()
    data = np.array(osc.read_timebase())[:-1]
    for i in range(0,samples):
        values = osc.read_waveform(channel=2)
        values = np.array(values)
        data = np.vstack([data, values])
    data = np.transpose(data)
    return data

def osc_meta(osc, file = None, first_line = None):
    f = open(file, 'a')
    if not first_line==None:
        f.write(first_line+'\n')                # Can pass first line of the report
    
    f.write(osc.device.query('*IDN?')+'\n') 

    f.write('-----\n\n')
    f.close()

def keithley_meta(k, file = None, first_line = None):
    f = open(file, 'a')
    if not first_line==None:
        f.write(first_line+'\n')                # Can pass first line of the report
    
    f.write(k.device.query('*IDN?')) 
    f.write('\nActive terminal: '+str(k.which_terminal()))
    f.write('Operating voltage [V] '+str(k.get_voltage())+'\n')
    # XX write definition for the following, also used later
    current_list = []
    current_meas_size = 10
    for current_meas in range(current_meas_size):
        current_list.append(k.get_current())    # Current measured in Amps
        time.sleep(0.1)
    current_array = np.array(current_list)
    f.write('Average current [A]   %.3e\n' % np.mean(current_array))
    f.write('Stdev current [A]     %.3e\n' % np.std(current_array))
    f.write('Measurement count     '+str(current_meas_size)+'\n')
    
    f.write('-----\n\n')
    f.close()

## XX Also save laser pulse rate    
def laser_meta(l, file = None, first_line = None):
    f = open(file, 'a')
    if not first_line==None:
        f.write(first_line+'\n')                # Can pass first line of the report
        
    f.write('\nQD Laser Control Settings\n')
    c_report = l.control_report()
    for line in c_report:
        f.write(line+'\n')
    f.write('\nQD Laser Monitor Values\n')
    m_report = l.monitor_report()
    for line in m_report:
        f.write(line+'\n')
    
    f.write('-----\n\n')
    f.close()

def motion_meta(m, file = None, first_line = None, misc = None):
    f = open(file, 'a')
    if not first_line==None:
        f.write(first_line+'\n')                # Can pass first line of the report
    
    if not misc==None:
        f.write('\nLinear mapping size {}\n'.format(misc[0]))
        f.write('Horizontal step {}\n'.format(misc[1]))
        f.write('Vertical step   {}\n'.format(misc[2]))
    f.write('step = 1 corresponds to 1.25 um\n')
    f.write('Vertical Laser Horizontal (position, uposition)\n')
    for k_name,v in m.devices.items():
        position = m.get_position(v)
        f.write('{} {} \n'.format(k_name,position))
    
    f.write('-----\n\n')
    f.close()
