import os
import pyvisa as visa
import matplotlib.pyplot as plt
import numpy as np

class agilent_mso6104A():

	def __init__(self,default_channel=1):
		rm=visa.ResourceManager()
		self.data_dict={}
		self.device=rm.open_resource("USB0::0x0957::0x1754::MY44000509::INSTR")
		print(self.device.query('*IDN?'))
		#self.device.write('OUTPut1:STAT OFF')
		self.default_channel=default_channel
		self.device.write(':WAVEFORM:FORMAT WORD')

	def take_data(self):
		self.device.write(':SINGLE')
		
	def triggered(self):
		return float(self.device.query(':TER?').strip())
		
	def acquire_mode(self,resolution=True):
		if resolution:
			self.device.write(':ACQUIRE:TYPE HRESOLUTION')
		else:
			self.device.write(':ACQUIRE:TYPE NORMAL')
		
	def read_waveform(self,channel, plot_with_clipped=False):
		if type(channel)==int or type(channel)==float:
			channel='CHANNEL'+str(channel)
		#self.device.write(':WAVEFORM:FORMAT WORD')
		clipped_low=False
		clipped_high=False
		self.device.write(':WAVEFORM:SOURCE '+channel)
		self.device.write(':WAVEFORM:DATA?')
		all_data=self.device.read_raw()
		data=all_data[10:].strip()
		yinc=float(self.device.query(':WAVEFORM:YINCREMENT?'))
		yorg=float(self.device.query(':WAVEFORM:YORIGIN?'))
		yref=float(self.device.query(':WAVEFORM:YREFERENCE?'))
		result=[]
		unclipped_result=[]
		for i in range(0,len(data),2):
			if data[i:i+2]==b'\x01\x00':
				clipped_low=True
			if data[i:i+2]==b'\xff\x00':
				clipped_high=True
			if plot_with_clipped and (data[i:i+2]==b'\xff\x00' or data[i:i+2]==b'\x01\x00'):
				result.append(None)
				datapoint=data[i]*256+data[i+1]
				unclipped_result.append(round(((datapoint-yref)*yinc+yorg),11))
			else:
				datapoint=data[i]*256+data[i+1]
				result.append(round(((datapoint-yref)*yinc+yorg),11))
				unclipped_result.append(round(((datapoint-yref)*yinc+yorg),11))
		
		if plot_with_clipped:
			return result,(clipped_low,clipped_high),unclipped_result
		else:
			return result,(clipped_low,clipped_high)
		
	def plot_waveform(self,channel=None):
		if not channel:
			channel=self.default_channel
		self.take_data()
		result1,clipped=self.read_waveform(channel)
		#result2,_=self.read_waveform('CHANNEL1')
		plt.plot(result1)
		#plt.title('Clipped_low'+str(clipped))
		#plt.plot(result2)
		plt.show()
	
	def set_scale(self,scale,units='mV',channel=None):
		if not channel:
			channel=self.default_channel
		self.device.write(':CHANNEL'+str(channel)+':SCALE '+str(scale)+units)
		return self.device.query(':CHANNEL'+str(channel)+':SCALE?')
	
	def get_range(self,channel=None):
		if not channel:
			channel=self.default_channel
		return self.device.query(':CHANNEL'+str(channel)+':RANGE?')
		
		
	def get_offset(self,channel=None):
		if not channel:
			channel=self.default_channel
		return float(self.device.query(':CHANNEL'+str(channel)+':OFFSET?'))
		
	def change_offset(self,delta,units='mV',channel=None):
		if not channel:
			channel=self.default_channel
		current_offset=float(self.device.query(':CHANNEL'+str(channel)+':OFFSET?'))
		if units=='mV':
			current_offset*=1000
		self.device.write(':CHANNEL'+str(channel)+':OFFSET '+str(current_offset+delta)+units)
	
	def set_offset(self,val,units='V',channel=None):
		self.device.write(':CHANNEL'+str(channel)+':OFFSET '+str(val)+units)
		
	def save_setup(self):
		self.device.query('SAVE:SETUP:START 0')
		
	def recall_setup(self):
		self.device.query('RECALL:SETUP:START 0')
	
	def get_scale(self,channel=None):
		if not channel:
			channel=self.default_channel
		return float(self.device.query(':CHANNEL'+str(channel)+':SCALE?'))*1000
		
	def set_timescale(self,value,units='ms'):
		self.device.write(':TIMEBASE:SCALE '+str(value)+' '+units)
		
	def get_timescale(self):
		return float(self.device.query(':TIMEBASE:SCALE?'))
		
	def set_timedelay(self,delay,units='ms'):
		self.device.write(':TIMEBASE:POSITION '+str(delay)+' '+units)
	
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

if __name__=='__main__':
    a=agilent_mso6104A()
		
'''
To try
:CHANnel1:OFFSet 0.200 V 
:CHANnel1:OFFSet?
:CHANnel1:RANGe?
:CHANnel1:SCALe?

:DIGITIZE
self.device.write(:WAVEFORM:DATA?)
all_data=self.device.read_raw()
xinc=inst.query(':WAVEFORM:XINCREMENT?')
yinc=inst.query(':WAVEFORM:YINCREMENT?')
xorg=inst.query(':WAVEFORM:XORIGIN?')
yorg=inst.query(':WAVEFORM:YORIGIN?')
xref=inst.query(':WAVEFORM:XREFERENCE?')
yref=inst.query(':WAVEFORM:YREFERENCE?')
'''