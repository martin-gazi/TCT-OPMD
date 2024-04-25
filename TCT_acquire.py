from Agilent_oscilloscope import agilent_mso6104A
from Keithley_control import keithley_2410
from Laser_control import Laser_IR
import numpy as np
import time

def get_Y_axis(osc):
    while True:
        try:
            osc.take_data()
            res,clipped=osc.read_waveform(channel=1)
        except IndexError:
            continue
        break
    return res

def get_X_axis(osc):
    step=osc.get_timescale()/100
    times=np.arange(0,1000*step,step)
    return times
    
def autoscale(osc,depth=0):
    if depth>40:
        print(r'Cannot set scale after {} steps'.format(depth))
        return False
    rang=[4.5,6,2] #[min_divisions,max_division,min_scale]
    data=get_Y_axis(osc)
    amp=(np.max(data)-np.min(data))*1000 # turn to mV
    current_scale=osc.get_scale()
    if rang[0]*current_scale<amp<rang[1]*current_scale or (current_scale<=rang[2] and amp<rang[1]*current_scale) :
        if not(depth==0):
            print(r'Scale changed to {}mV in {} steps'.format(current_scale, depth)) #specify
        return True
    elif rang[1]*current_scale<amp:
        osc.set_scale(max(round(current_scale*1.25),round(current_scale+1)))
        return autoscale(osc,depth=depth+1)
    elif rang[0]*current_scale>amp:
        new_scale=max(round(amp/5.5),rang[2])
        osc.set_scale(new_scale)
        return autoscale(osc,depth=depth+1)

def ramp_voltage(k, target_voltage):
    if target_voltage is None:
        target_voltage = k.get_voltage()
    current_voltage = k.get_voltage()
    voltage_diff = target_voltage - current_voltage
    if voltage_diff == 0:
        print(r'Voltage kept at {}V'.format(current_voltage))
    elif abs(voltage_diff) <= 30:
        k.set_voltage(target_voltage)
        print(r'Voltage changed from {}V to {}V in 1 step'.format(current_voltage, target_voltage))    
    else:
        steps = 10
        for i in range(steps):
            k.set_voltage(current_voltage + voltage_diff*(i+1)/steps)
            time.sleep(1)
        print(r'Voltage changed from {}V to {}V over {} steps'.format(current_voltage, target_voltage, steps))

# Under construction
def get_breakdown(k, max_allowed_voltage=500):
    ramp_voltage(k, 0)
    precision_step=-5
    while not k.in_compliance():
        current_voltage = k.get_voltage()
        if current_voltage <= -abs(max_allowed_voltage):
            break
        k.set_voltage(current_voltage+precision_step)
        time.sleep(1)
    breakdown_voltage = current_voltage
    print(r'Breakdown voltage {}V within {}V'.format(breakdown_voltage, abs(precision_step)))
    return breakdown_voltage

def run_routine(k, osc, l, frequency=50, DAC=1320):
    time.sleep(0.1)
    l.turn_off()
    time.sleep(0.1)
    l.set_dac(dac_val=DAC)
    time.sleep(0.1)
    l.turn_on(freq=frequency)
    
    # preset starting voltage manually
    start_voltage = k.get_voltage()
    end_voltage = 0
    step_voltage = 5
    IV=[]
    
    for present_voltage in range(int(start_voltage), end_voltage+step_voltage, step_voltage):
        time.sleep(0.1)
        k.set_voltage(present_voltage)
        time.sleep(2)
        IV.append([k.get_voltage(), k.get_current()])
        autoscale(osc)
        time.sleep(1)
        
        sample_size = 1000
        data=[]
        data.append(get_X_axis(osc))
        for j in range(sample_size):
            data.append(get_Y_axis(osc))
        data = np.array(data)
        file_name=r'output/LGAD_W2_{}Hz_DAC{}_{}V.npy'.format(frequency, DAC, abs(present_voltage))
        np.save(file_name, data)
    
    IV = np.array(IV)
    IV_file_name=r'output/IV_LGAD_W2_{}Hz_DAC{}.npy'.format(frequency, DAC)
    np.save(IV_file_name, IV)
    print('{} samples saved per voltage point'.format(sample_size))
        
    
if __name__=='__main__':
    k=keithley_2410(address=24,gpib_num=0)
    osc=agilent_mso6104A()
    l=Laser_IR()
    
    l.turn_on()
    k.initialize_IV(compliance_in_amps=0.000005)
    k.switch_rear_terminal()
    freq_values = [50, 200, 1000]
    DAC_values = [1650, 1980, 2145, 2310]
    # DAC_values = [66, 330, 660]
    breakdown_voltage = get_breakdown(k)
    
    for freq_index in range(len(freq_values)):
        for DAC_index in range(len(DAC_values)):
            ramp_voltage(k, breakdown_voltage)
            run_routine(k, osc, l, freq_values[freq_index], DAC_values[DAC_index])
    
    l.turn_off()
    ramp_voltage(k,0)
    k.turn_off()

# 10% 330[mV]
# 20% 660[mV]
# 30% 990[mV]
# 40% 1320[mV]
# 50% 1650[mV]
# 60% 1980[mV]
# 70% 2310[mV]
# 80% 2640[mV]
# 90% 2970[mV]
# 100% 3300[mV]