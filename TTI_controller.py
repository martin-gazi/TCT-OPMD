import serial
import time

class TTI_QL355TP():

	def __init__(self, main_channel=1):
	
		self.data_dict={}
		self.main_channel=main_channel
		
		ser = serial.Serial(port='COM8',
			baudrate=9600,
			parity=serial.PARITY_NONE,
			stopbits=serial.STOPBITS_ONE,
			bytesize=serial.EIGHTBITS
		)
		if not ser.isOpen():
			ser.open()
		self.device=ser
		print(self.write_ser('*IDN?'))

	#self.write_ser('OVP1 6')
	#self.write_ser('OVP2 6')
	#self.write_ser('OCP2 1')
	#self.write_ser('OCP1 1')
    
	def write_ser(self,arg,time_wait=0.3):
		self.device.write((arg+'\r\n').encode())
		time.sleep(time_wait)
		if self.device.inWaiting()>0:
			data=self.device.read(self.device.inWaiting())
			return data.decode().strip()

	def turn_on(self,channel=None):
		if channel==1 or channel==2:
			self.write_ser('OP'+str(channel)+' 1')
		else:
			self.write_ser('OPALL 1')

	def turn_off(self,channel=None):
		if channel==1 or channel==2:
			self.write_ser('OP'+str(channel)+' 0')
		else:
			self.write_ser('OPALL 0')
	
	def set_voltage(self,volts):

		self.write_ser('V'+str(self.main_channel)+' '+str(volts))
	
	def get_current(self):
		return float(self.write_ser('I'+str(self.main_channel)+'O?').strip()[:-1])

	def get_voltage(self):
		return float(self.write_ser('V'+str(self.main_channel)+'O?').strip()[:-1])
		
	def __del__(self):
		self.device.close()
		


if __name__=='__main__':
	lv=TTI_QL355TP()
	lv.get_current()
