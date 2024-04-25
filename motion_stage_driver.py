from ctypes import *
import time
import os
import sys
import platform
import tempfile
import re

if sys.version_info >= (3,0):
    import urllib.parse
    
cur_dir = os.path.abspath(os.path.dirname(__file__))
ximc_dir = os.path.join(cur_dir, "ximc")
ximc_package_dir = os.path.join(ximc_dir, "crossplatform", "wrappers", "python")
sys.path.append(ximc_package_dir)  # add ximc.py wrapper to python path

if platform.system() == "Windows":
    arch_dir = "win64" if "64" in platform.architecture()[0] else "win32"
    libdir = os.path.join(ximc_dir, arch_dir)
    os.environ["Path"] = libdir + ";" + os.environ["Path"]  # add dll
    if sys.version_info.minor>7:
        os.add_dll_directory(libdir)


try: 
    from pyximc import *
except ImportError as err:
    print ("Can't import pyximc module. The most probable reason is that you changed the relative location of the testpython.py and pyximc.py files. See developers' documentation for details.")
    exit()
except OSError as err:
    print(err)
    print ("Can't load libximc library. Please add all shared libraries to the appropriate places. It is decribed in detail in developers' documentation. On Linux make sure you installed libximc-dev package.\nmake sure that the architecture of the system and the interpreter is the same")
    exit()

translation_dict={'8MT30-50':'H','Axis 1':'L','Axis 2':'V'}

		
class MotionStageController():
	def __init__(self):
		self.big_step_threshold=900
		self.position_emitters={}
		self.sbuf = create_string_buffer(64)
		lib.ximc_version(self.sbuf)
		print("Library version: " + self.sbuf.raw.decode().rstrip("\0"))
		
		lib.set_bindy_key(os.path.join(ximc_dir, "win32", "keyfile.sqlite").encode("utf-8"))
		
		# This is device search and enumeration with probing. It gives more information about devices.
		probe_flags = EnumerateFlags.ENUMERATE_PROBE + EnumerateFlags.ENUMERATE_NETWORK
		enum_hints = b"addr=192.168.0.1,172.16.82.165"
		# enum_hints = b"addr=" # Use this hint string for broadcast enumerate
		devenum = lib.enumerate_devices(probe_flags, enum_hints)
		
		dev_count = lib.get_device_count(devenum)
		print(dev_count)
		if dev_count!=3:
			raise Exception('Did not find EXACTLY 3 devices that resemble motion stages')
		
		self.controller_name = controller_name_t()
		self.define_needed_objects()
		#iterate devices
		names=[]
		for dev_ind in range(0, dev_count):
			enum_name = lib.get_device_name(devenum, dev_ind)
			result = lib.get_enumerate_device_controller_name(devenum, dev_ind, byref(self.controller_name))
			if result == Result.Ok:
				print("#{} : ".format(dev_ind) + repr(enum_name) + ". Name: " + repr(self.controller_name.ControllerName) + ".")
				names.append(self.controller_name.ControllerName.decode())
				
		self.devices={}
		for i,name in enumerate(names):
			open_name = lib.get_device_name(devenum, i)
			if type(open_name) is str:
				open_name = open_name.encode()
			self.devices[translation_dict[name]]=lib.open_device(open_name)
			
	def define_needed_objects(self):
		self.x_pos = get_position_t()
		self.mvst = move_settings_t()
		
	def assign_emitter(self,emitter_object):
		if emitter_object.id in self.devices.values():
			self.position_emitters[emitter_object.id]=emitter_object
		else:
			print('Could not assign emitter!')
		
	def get_position(self, device_id):
		result = lib.get_position(device_id, byref(self.x_pos))
		if device_id in self.position_emitters:
			self.position_emitters[device_id].t=self.x_pos.Position
		return self.x_pos.Position, self.x_pos.uPosition
		
	def get_speed(self, device_id)        :		
		result = lib.get_move_settings(device_id, byref(mvst))
		return self.mvst.Speed
		
	def set_speed(self, device_id, speed):
		result = lib.get_move_settings(device_id, byref(self.mvst))
		self.mvst.Speed = int(speed)
		result = lib.set_move_settings(device_id, byref(self.mvst))

	def test_status(self, device_id):
		print("\nGet status")
		x_status = status_t()
		result = lib.get_status(device_id, byref(x_status))
		if result == Result.Ok:
			print("Status.Ipwr: " + repr(x_status.Ipwr))
			print("Status.Upwr: " + repr(x_status.Upwr))
			print("Status.Iusb: " + repr(x_status.Iusb))
			print("Status.Flags: " + repr(hex(x_status.Flags)))
			
	def wait_for_stop(self, device_id, interval=100):
		result = lib.command_wait_for_stop(device_id, interval)

	def move(self, device_id, distance, udistance):
		result = lib.command_move(device_id, distance, udistance)
		self.wait_for_stop(device_id)
		
	def breakdown_step(self,step):
		abs_step=abs(step)
		sign=int(step/abs_step)
		min_step=5
		return [min_step*sign]*(abs_step//min_step)+[(abs_step%min_step)*sign]
			
	def rel_move(self,device_id,step):
		if abs(step)>self.big_step_threshold:
			raise Exception('Too big of a step. Dangerous!')
			
		result=lib.command_movr(device_id,step,0)
		self.wait_for_stop(device_id)		
		self.get_position(device_id)
		
	def stopall(self):
		for k,v in self.devices.items():
			lib.command_stop(v)

	def __del__(self):
		for id in self.devices.values():
			lib.close_device(byref(cast(id, POINTER(c_int))))

if __name__=='__main__':
	m=MotionStageController()
	for k,v in m.devices.items():
		print(k,m.get_position(v))