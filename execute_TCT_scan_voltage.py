import sys,traceback,time,random,os,shutil,datetime
import numpy as np
import matplotlib.pyplot as plt

from Keithley_control import keithley_2410
from RTP044_oscilloscope import rhodeschwarz_rtp044
from QD_Laser_control import QD_Laser

from cmd_lib import ramp_voltage, autoscale, wave_acquire
from cmd_lib import osc_meta, keithley_meta, laser_meta

def save_grid(grid, name, label=''):        # Misnomer - relict from 2D_scan
    plt.subplot()
    plt.plot(-volt_array, grid)
    plt.xlabel('Bias voltage [V]')
    plt.ylabel(label)
    plt.savefig('{}/{}_{}.png'.format(path, output_file, name), bbox_inches='tight')
    plt.clf()

### ------------------------------------------------------------------------------------

k   =   keithley_2410(address=24,gpib_num=0)
osc =   rhodeschwarz_rtp044()
l   =   QD_Laser()

### Metadata file initialization
timestr = time.strftime("%Y%m%d-%H%M%S")
meta_temp_file = 'temp_meta.txt'
f = open(meta_temp_file, 'w')
f.write(timestr+'\n-----\n\n')
f.close()

log_temp_file = 'temp_log.txt'  #XX write log print function which does both?
g = open(log_temp_file, 'w')
g.write(timestr+'\n-----\n\n')
g.close()

output_path = 'C:/LGAD_data/voltage_scan_data'
output_folder = 'W2_PiN1_1_{}'.format(timestr)
path = os.path.join(output_path, output_folder)
print(path)
output_file   = 'W2_PiN1_1'
try: 
    os.makedirs(path)
except OSError as error: 
    print(error)
# XX Have another file - log, which will show the same thing as is outputted by print?

### Initialization of RTP044 oscilloscope
osc.run()
osc.screen_on()
# XX set default mode osc?
# XX define trigger and measure channel in the script? make it easier to change?
osc_meta(osc, file = meta_temp_file,
   first_line = 'Pre-measurement Rohde&Schwarz report')
osc.save_screenshot(path=path,name='{}_RTP_0'.format(output_file),trig=True)

### Initialization of Keithley voltage source
k.initialize_IV(compliance_in_amps=0.000005)    # Compliance set to 5 uA
k.switch_rear_terminal()                        # Using rear terminal
k.turn_on()
ramp_voltage(k, target_voltage = 0)
keithley_meta(k, file = meta_temp_file, 
    first_line = 'Pre-measurement Keithley report (laser OFF)')

### Measurement range definition
start_bias = -5      # Negative - starting bias (least negative)
final_bias = -260    # Negative - final bias (most negative)
step_bias  = -1      # Negative - step taken between measurements
volt_array = np.arange(start_bias, final_bias+step_bias, step_bias)
# XX known problem, if range not divisible by step_bias, voltage goes above final_bias!

### Initialization of QD laser
l.set_gate(value = 830)     # Default gate voltage setting to 830 mV
l.set_bias(value = 9)       # Default bias current setting to 9 mA
l.set_temp(value = 20)      # Default temperature setting to 20 degC
# XX Set firing rate
l.trigger_on()
l.tec_on()
l.current_on()
time.sleep(2)
laser_meta(l, file = meta_temp_file, 
    first_line = 'Pre-measurement QD Laser report')

### Array definition for the final plot
total_points = len(volt_array)
grid = np.zeros(len(volt_array))
jitter_grid  = grid.copy()
slew_grid    = grid.copy()
amp_grid     = grid.copy()
area_grid    = grid.copy()
low_grid     = grid.copy()
count_grid   = grid.copy()
current_grid = grid.copy()

### Initialize array for output
### out_size is 1 (voltage) + 2*number of meas + 1 (wave counts) + 3 (current, std, count)
out_size = 15       
out = np.empty((0,out_size))      

# XX move the laser to a better position before starting measurement? 
# XX problem with initial_position used later, would need to have a new variable
### Main loop - also keeps track of time
g = open(log_temp_file, 'a')
start_time = time.time()
for set_volt in volt_array:
    point_start_time = time.time()
    msg=ramp_voltage(k, target_voltage = set_volt)
    g.write(msg+'\n')
    if k.in_compliance():
        break
    msg=autoscale(osc)                       # XX autoscale does not seem to be working very well
                                             # Mainly sets scale too small and then fails to adjust
                                             # leading to signals too big for the scope
    g.write(msg+'\n')
    time.sleep(0.5)                         # Such that the signal can settle if averaged
    for group_no in range(1,6):
        osc.clear_meas(group = group_no)    # XX better command to clear all groups?
        
    current_acquisition_time = 2                # Current acquision time at one point (s)
        # XX the above is not so useful if also wave_acquire is used later
    current_sleep_time = 0.1                    # Time between current measurements
    current_list = []
    current_meas_size = int(current_acquisition_time/current_sleep_time)
    osc.run()                                   # Data taking started
    for current_meas in range(current_meas_size):
        current_list.append(k.get_current())    # Current measured in Amps
        time.sleep(current_sleep_time)
    current_array = np.array(current_list)
    osc.stop()                                  # Data taking stopped

    op_volt      = k.get_voltage()
    mean_delay   = float(osc.get_meas(group=1))     # Pre-set OSC for trig 50% - signal 50%
    std_delay    = float(osc.get_meas_std(group=1))
    mean_slew    = float(osc.get_meas(group=2))     # Pre-set OSC for 49%-51% range
    std_slew     = float(osc.get_meas_std(group=2))
    mean_amp     = float(osc.get_meas(group=3))
    std_amp      = float(osc.get_meas_std(group=3))
    mean_area    = float(osc.get_meas(group=4))     # Pre-set OSC for 0 V level
    std_area     = float(osc.get_meas_std(group=4))
    mean_low     = float(osc.get_meas(group=5))
    std_low      = float(osc.get_meas_std(group=5))
    count        = int(osc.get_meas_count(group=5))
    mean_current = np.mean(current_array)
    std_current  = np.std(current_array)
    
    out_point = [op_volt,  \
                 mean_delay,   std_delay,   mean_slew,   std_slew, \
                 mean_amp,     std_amp,     mean_area,   std_area, \
                 mean_low,     std_low,     count, \
                 mean_current, std_current, current_meas_size]
    
    # XX separate process for now, can add above next, this is to get approx save stats for above
    save_waveforms = True
    if save_waveforms:
        osc.run()
        wfs=wave_acquire(osc, samples=10)          # Gets waveforms, however not the same data!
        osc.stop()  
        np.savetxt('{}/wf_{}_{}V.csv'.format(path, output_file, abs(set_volt)), 
            wfs, delimiter=',', fmt='%.4e')
    # XX potentially use this to record 1000 points and shorten keithley 
    # XX acq time to 0.01 and just do a quick one beforehand
    # XX also uses 125 fs resolution, overkill and also large files as a result
    
    point_index, = np.where(volt_array == set_volt)
    point_index = point_index[0]
    done_points = point_index+1
    point_time = time.time()-point_start_time
    elap_time = time.time()-start_time
    remain_time = total_points*elap_time/done_points-elap_time
    msg = 'Voltage {} V done! Finished {} out of {}'.format(set_volt, done_points, total_points)
    print(msg)
    g.write(msg+'\n')
    msg = 'Meas time: {} s. Total elapsed time: {}. Est remaining time: {} (h:m:s)'.format(
        round(point_time,1), 
        datetime.timedelta(seconds=round(elap_time)), 
        datetime.timedelta(seconds=round(remain_time)))
    print(msg)
    g.write(msg+'\n\n')
    print(out_point)
    out = np.vstack((out, np.array(out_point)))
    
    jitter_grid[point_index]  = std_delay
    slew_grid[point_index]    = mean_slew     
    amp_grid[point_index]     = mean_amp
    area_grid[point_index]    = mean_area
    low_grid[point_index]     = mean_low      
    count_grid[point_index]   = count
    current_grid[point_index] = mean_current      
msg = ramp_voltage(k, target_voltage = 0)
g.write(msg+'\n')
g.close()
        
acq_time=time.time()-start_time
acq_time_hms=datetime.timedelta(seconds=round(acq_time))
print(r'Acquisition time {} (h:m:s)'.format(acq_time_hms))
f = open(meta_temp_file, 'a')
f.write((r'Acquisition time {} (h:m:s)'.format(acq_time_hms))+'\n-----\n\n')
f.close()
osc.save_screenshot(path=path,name='{}_RTP_1'.format(output_file),trig=False)

### Turn QD laser off
laser_meta(l, file = meta_temp_file, 
    first_line = 'Post-measurement QD Laser report')
l.trigger_off()
l.tec_off()
l.current_off()

### Turn Keithley voltage source off
keithley_meta(k, file = meta_temp_file, 
    first_line = 'Post-measurement Keithley report (laser OFF)')
ramp_voltage(k, target_voltage = 0)
k.turn_off()

### Saving data and metadata
np.savetxt('{}/{}.csv'.format(path, output_file), out, delimiter=",")
meta_dest_file='{}/{}_meta.txt'.format(path, output_file)
shutil.copyfile(meta_temp_file, meta_dest_file, follow_symlinks=True)
log_dest_file='{}/{}_log.txt'.format(path, output_file)
shutil.copyfile(log_temp_file, log_dest_file, follow_symlinks=True)
# XX save metadata (osc)

### Saving grid previews
save_grid(grid=jitter_grid, name='jitter', label='Jitter [s]')
save_grid(grid=slew_grid,   name='slew',   label='Slew rate [V/s]') 
save_grid(grid=amp_grid,    name='amp',    label='Amplitude [V]')
save_grid(grid=area_grid,   name='area',   label='Area [Vs]')
save_grid(grid=low_grid,    name='low',    label='Low [V]')
save_grid(grid=count_grid,  name='count',  label='Wave count')
save_grid(grid=current_grid,name='current',label='Current [A]')