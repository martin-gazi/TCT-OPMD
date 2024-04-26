import pyvisa as visa
import numpy as np
import time

class keithley_2410():

	def __init__(self, address=23, gpib_num=1):
		rm=visa.ResourceManager()
		self.data_dict={}
		self.device=rm.open_resource("GPIB"+str(gpib_num)+"::"+str(address)+"::INSTR")
		print(self.device.query('*IDN?'))
		#self.device.write('OUTPut1:STAT OFF')

	def in_compliance(self):
		return bool(float(self.device.query('SENS:CURR:PROT:TRIP?')))

	def initialize_IV(self, compliance_in_amps=0.000005):
		self.device.write('SENS:FUNC "CURR"') # sense current
		self.device.write('SOUR:VOLT:RANG 200') # +/- 200V
		self.device.write('SENS:CURR:PROT:LEV '+str(compliance_in_amps))
		self.device.write('OUTPut1:STAT ON')
		self.data_dict['compliance']=compliance_in_amps

	def switch_rear_terminal(self):
		self.device.write(':ROUTe:TERMinals REAR')
		self.device.write('OUTPut1:STAT ON')

	def switch_front_terminal(self):
		self.device.write(':ROUTe:TERMinals FRONt')
		self.device.write('OUTPut1:STAT ON')

	def which_terminal(self):
		return self.device.query(':ROUTe:TERMinals?')

	def turn_off(self):
		self.device.write('OUTPut1:STAT OFF')
		self.set_voltage(0)

	def turn_on(self):
		self.device.write('OUTPut1:STAT ON')

	def set_voltage(self,volts,special=False):
		if volts>0 and not special:
			volts*=-1
			print('volts are +, making them -')
		self.device.write('SOUR:VOLT:LEV:IMM:AMPL '+str(volts))
	
	def get_data(self):
		self.device.write(':INIT')
		return self.device.query('FETC?')
		
	def get_current(self):
		data=self.get_data()
		return float(data.split(',')[1])
		
	def get_voltage(self):
		data=self.get_data()
		return float(data.split(',')[0])	
		
	def do_IV_Investigator(self,start=-6,end=-20,steps=30,samples=10,other_keithley=None,step_sleep=1,rounded=1):
		voltages=np.linspace(start,end,steps)
		self.set_voltage(start)
		time.sleep(3)
		v=[]
		i=[]
		i_r=[]
		for v_current in voltages:
			self.set_voltage(round(v_current,rounded))
			v.append(v_current)
			time.sleep(step_sleep)
			i_sample=[]
			i_r_sample=[]
			for _ in range(samples):
				i_sample.append(self.get_current())
				if other_keithley!=None:
					i_r_sample.append(other_keithley.get_current())
			i.append(np.array(i_sample))
			i_r.append(np.array(i_r_sample))
			print(v_current,np.mean(i_sample))
		
		return np.hstack((np.array(i),np.array(v).reshape(len(v),1))),np.array(i_r)
		
class mega_keithley():

	def __init__(self, address=23, gpib_num=1):
		rm=visa.ResourceManager()
		self.data_dict={}
		self.device=rm.open_resource("GPIB"+str(gpib_num)+"::"+str(address)+"::INSTR")
		print(self.device.query('*IDN?'))
		#self.device.write('OUTPut1:STAT OFF')


	def initialize_IV_SCC(self):
		compliance_in_amps=0.00005  #default 0.0000025 for fei4 quads
		self.device.write('SENS:FUNC "CURR"') # sense current
		self.device.write('SOUR:VOLT:RANG 200') # +/- 200V
		self.device.write('SENS:CURR:PROT:LEV '+str(compliance_in_amps))
		self.device.write('OUTPut1:STAT ON')
		self.data_dict['compliance']=compliance_in_amps

	def turn_off(self):
		self.device.write('OUTPut1:STAT OFF')
		self.set_voltage(0)

	def set_voltage(self,volts,special=False):
		if volts>0 and not special:
			volts*=-1
			print('volts are +, making them -')
		self.device.write('SOUR:VOLT:LEV:IMM:AMPL '+str(volts))
	
	def get_data(self):
		#self.device.write(':INIT')
		return self.device.query('FETC?')
		
	def get_current(self):
		data=self.get_data()
		return float(data.split(',')[0][:-4])
		

if __name__=="__main__":
	k=keithley_2410(address=24,gpib_num=0)