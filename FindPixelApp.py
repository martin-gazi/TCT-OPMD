from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import sys,traceback,time,random,os
from motion_stage_driver import MotionStageController
import numpy as np
from collections import defaultdict

from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
import matplotlib.pyplot as plt

import importlib
import threading
import LaserScanImporter
from colorama import init,Fore,Style

init(convert=True)


cache_dir='.\\Cache'
data_dir='.\\data'
if not os.path.exists(cache_dir):
    os.makedirs(cache_dir)
	
if not os.path.exists(data_dir):
    os.makedirs(data_dir)

class WorkerSignals(QObject):
	finished = pyqtSignal()
	error = pyqtSignal(tuple)
	result = pyqtSignal(object)
	progress = pyqtSignal(int)
	
class Worker(QRunnable):
	def __init__(self, fn, *args, **kwargs):
		super(Worker, self).__init__()

		# Store constructor arguments (re-used for processing)
		self.fn = fn
		self.args = args
		self.kwargs = kwargs
		self.signals = WorkerSignals()	

		# Add the callback to our kwargs
		self.kwargs['progress_callback'] = self.signals.progress		

	@pyqtSlot()
	def run(self):
		'''
		Initialise the runner function with passed args, kwargs.
		'''
		
		# Retrieve args/kwargs here; and fire processing using them
		try:
			result = self.fn(*self.args, **self.kwargs)
		except:
			traceback.print_exc()
			exctype, value = sys.exc_info()[:2]
			self.signals.error.emit((exctype, value, traceback.format_exc()))
		else:
			self.signals.result.emit(result)  # Return the result of the processing
		finally:
			self.signals.finished.emit()  # Done
			
	@pyqtSlot()	
	def stop(self):
			self.threadactive = False
			self.wait()


class TwoDScanParamters(QWidget):
	def __init__(self,*args,**kwargs):
		super().__init__(*args,**kwargs)
		self.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.MinimumExpanding)
		self.load_default_parameters()
		
		self.label1=QLabel('Begin')
		self.label2=QLabel('End')
		self.label3=QLabel('Step')
		
		names=['Laser','Hor','Ver']
		self.labels=[]
		for c in names:
			self.labels.append(QLabel(c))
			
		
		self.edit_boxes=[]
		for i in range(10):
			self.edit_boxes.append(self.make_line_edit(i))
			
		layout=QGridLayout(self)
		for i,l in enumerate(self.labels):
			layout.addWidget(l,i+1,0)
		layout.addWidget(self.label1,0,1)
		layout.addWidget(self.label2,0,2)
		layout.addWidget(self.label3,0,3)
		for i,box in enumerate(self.edit_boxes[:-1]):
			layout.addWidget(box,i//3+1,i%3+1,1,1,Qt.AlignCenter)
		layout.addWidget(self.edit_boxes[-1],0,0,1,1,Qt.AlignCenter)
		
	def make_line_edit(self,i):
		le= QLineEdit()
		le.setValidator(QIntValidator())
		le.setAlignment(Qt.AlignCenter)
		le.setText(str(self.parameters[i]))
		le.textChanged.connect(self.change_parameter(i))
		return le
		
	def change_parameter(self,i):
		def inner_function(text):
			try:
				self.parameters[i]=int(text)
			except ValueError:
				self.parameters[i]=0
			np.savetxt(self.cache_file,self.parameters)
		return inner_function
		
	def load_default_parameters(self):
		self.channels=[1,3,4]
		self.cache_file=os.path.join(cache_dir,'scan_parameters.txt')
		if os.path.isfile(self.cache_file):
			self.parameters=np.loadtxt(self.cache_file)
			self.parameters=self.parameters.astype(np.int)
		else:
			self.parameters=np.array([0,0,0,0,0,0,0,0,0,1])
			np.savetxt(self.cache_file,self.parameters)
			
class TwoDScan(QWidget):
	def __init__(self,*args,**kwargs):
		super().__init__()
		self.m=args[0]
		
		self.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.MinimumExpanding)
		self.figure = plt.figure()
		self.canvas = FigureCanvas(self.figure)
		self.canvas.setFixedWidth(300)
		self.canvas.setFixedHeight(300)
		self.toolbar = NavigationToolbar(self.canvas, self)
		self.button_plot = QPushButton('Run')
		self.twodscan_parameters=TwoDScanParamters()
		self.event_stop=threading.Event()
		
		self.threadpool = QThreadPool()
		
		layout=QVBoxLayout(self)
		layout.addWidget(self.toolbar,Qt.AlignCenter)
		layout.addWidget(self.canvas,Qt.AlignCenter)
		layout.addWidget(self.button_plot,Qt.AlignCenter)
		layout.addWidget(self.twodscan_parameters,Qt.AlignCenter)

	def plot(self,data,l):
		ax = self.figure.add_subplot(111)
		ax.clear()
		ax.imshow(data,cmap='jet')
		ax.set_title('L: '+str(l))
		self.canvas.draw()

	def get_amplitude(self,waveform):
		return np.mean(waveform[0:100])-np.min(waveform)

	def thread_complete(self):
		self.button_plot.setEnabled(True)
		
	def stop(self):
		self.event_stop.set()
		print(Fore.RED+'Scan stopped!',Style.RESET_ALL)
	
		self.button_plot.setEnabled(False)
		
		spaces,h_return,v_return=self.get_scanning_space()
		if not spaces:
			raise Exception('Scan cancelled')
		
		#import module every time a scan is random
		importlib.reload(LaserScanImporter)
		lsi=LaserScanImporter.LaserScanImporter()
		
		for current_loop in range(lsi.scan_loops):
			lsi.scan_current_loop=current_loop
			lsi.function_executed_at_scan_begin(osc)
			#Move to beginning of scan
			udist={}
			for k in spaces.keys():
				udist[k]=self.m.get_position(self.m.devices[k])[1]
				#self.m.move(self.m.devices[k],spaces[k],udist[k])
			channels=self.twodscan_parameters.channels
			final_data_form=np.zeros((1,1003,3)).astype(np.float)#1000 scope datapoints and 3 for position
			counter=0
			data_file=0
			img_data=np.zeros((len(spaces['V']),len(spaces['H'])))
			for l in spaces['L']:
				self.m.move(self.m.devices['L'],l,udist['L'])
				for v in spaces['V']:
					self.m.move(self.m.devices['V'],v,udist['V'])
					for h in spaces['H']:
						self.m.move(self.m.devices['H'],h,udist['H'])
						data=defaultdict(list)
						for _ in range(self.twodscan_parameters.parameters[9]):
							while True:
								try:
									if self.event_stop.is_set():
										raise Exception('Killing scan...')
									osc.take_data()
									for c in channels:
										res,clipped=osc.read_waveform(channel=c)
										data[c].append(np.array(res))
								except IndexError:
									continue
								break
						for c in channels:
							data[c]=np.mean(data[c],axis=0)
							if c==1: #plot channel 1
								amplitude=self.get_amplitude(data[c])
								img_data[spaces['V'].index(v),spaces['H'].index(h)]=amplitude
								self.plot(img_data,l)
								
							final_data_form[0,:1000,channels.index(c)]=data[c]
							final_data_form[0,1000:,channels.index(c)]=[h,v,l]
						if counter==0:
							final_data=np.copy(final_data_form)
						else:
							final_data=np.vstack((final_data_form,final_data))
						counter+=1
						if counter>0 and counter%1000==0: #save every 1000 waveforms
							np.save(os.path.join(data_dir,lsi.prefix+'_1000points_position_last_3_'+str(data_file)+'.npy'),final_data)
							del final_data
							data_file+=1
							counter=0
					if h_return is not None:
						for h_r in h_return: # return slowly to beginning position
							self.m.move(self.m.devices['H'],int(h_r),udist['H'])
							time.sleep(0.1)
				if v_return is not None:
					for v_r in v_return: # return slowly to beginning position
						self.m.move(self.m.devices['V'],int(v_r),udist['V'])
						time.sleep(0.1)
			if counter>0:
				np.save(os.path.join(data_dir,lsi.prefix+'_1000points_position_last_3_'+str(data_file)+'.npy'),final_data)
				counter=0
				del final_data
			lsi.function_executed_at_scan_end(osc)
	def get_scanning_space(self):
		max_difference=3000
		spaces={}
		p=self.twodscan_parameters.parameters
		spaces['L']=list(range(p[0],p[1],p[2]))
		spaces['H']=list(range(p[3],p[4],p[5]))
		spaces['V']=list(range(p[6],p[7],p[8]))
		for k,v in spaces.items():
			if len(v)<=0:
				print(Fore.GREEN+'Something wrong with limit of ',k,Style.RESET_ALL)
				return None,None,None
			if np.all(np.abs(np.array(v)-self.m.get_position(self.m.devices[k])[0])>max_difference):
				print(Fore.GREEN+'Too big of a jump in ',k,Style.RESET_ALL)
				return None,None,None
		
		max_horizontal_return_step=100
		if (spaces['H'][-1]-spaces['H'][0])>2*max_horizontal_return_step:
			horizontal_return=np.linspace(spaces['H'][-1],spaces['H'][0],int((spaces['H'][-1]-spaces['H'][0])/max_horizontal_return_step)).astype(int)
		else:
			horizontal_return=None
			
		max_vertical_return_step=5
		if (spaces['V'][-1]-spaces['V'][0])>2*max_vertical_return_step:
			vertical_return=np.linspace(spaces['V'][-1],spaces['V'][0],int((spaces['V'][-1]-spaces['V'][0])/max_vertical_return_step)).astype(int)
		else:
			vertical_return=None
				
		return spaces,horizontal_return,vertical_return
				


class ValueAssign(QWidget): #unused
	valueChanged = pyqtSignal(object)

	def __init__(self, name, parent=None):
		super(ValueAssign, self).__init__(parent)
		self._t = 0
		self.id = name

	@property
	def t(self):
		return self._t

	@t.setter
	def t(self, value):
		self._t = value
		self.valueChanged.emit(value)

class _Motion_Stage_Row(QWidget):
	def __init__(self,*args,**kwargs):
		new_kwargs=self.load_defaults(*args,**kwargs)
		super().__init__(*args,**new_kwargs)
		
		self.setSizePolicy(QSizePolicy.MinimumExpanding,QSizePolicy.MinimumExpanding)

		self.threadpool = QThreadPool()
		print("Multithreading with maximum %d threads" % self.threadpool.maxThreadCount())

		button1 = QPushButton('Dec')
		button2 = QPushButton('Inc')
		button1.clicked.connect(self.stage_relative_move(-1))
		button2.clicked.connect(self.stage_relative_move(1))
		
		
		self.motion_position = QLineEdit()
		self.motion_position.setValidator(QIntValidator())
		self.motion_position.setAlignment(Qt.AlignCenter)
		self.motion_position.setReadOnly(True)
		self.motion_position.setStyleSheet("QLineEdit { background: rgb(220, 220, 220); }")
		
		
		self.motion_step = QLineEdit()
		self.motion_step.setValidator(QIntValidator())
		self.motion_step.setAlignment(Qt.AlignCenter)
		self.motion_step.setText(str(self.movement_step))
		self.motion_step.textChanged.connect(self.step_change)
		
		self.motion_label=QLabel(self.stage_name)
		
		#self.value_assign=ValueAssign(self.stage_id)
		#self.value_assign.valueChanged.connect(self.change_motion_position) #testing
		#self.m.assign_emitter(self.value_assign)
		
		layout=QHBoxLayout(self)
		layout.addWidget(self.motion_label,Qt.AlignCenter)
		layout.addWidget(button1,Qt.AlignCenter)
		layout.addWidget(self.motion_position,Qt.AlignCenter)
		layout.addWidget(button2,Qt.AlignCenter)
		layout.addWidget(self.motion_step,Qt.AlignCenter)
		

		#self.m.get_position(self.stage_id)

	def load_defaults(self,*args,**kwargs):
		self.movement_step=10
		self.stage_name='Test name'
		found_keys=[]

		for k,v in kwargs.items():
			if k=='stage_label':
				self.stage_name=v
				found_keys.append(k)
			if k=='stage_id':
				self.stage_id=v
				found_keys.append(k)
			if k=='motion_stage_controller':
				self.m=v
				found_keys.append(k)
		for item in found_keys:
			kwargs.pop(item)
		
		return kwargs

	def step_change(self,text):
		try:
			self.movement_step=abs(int(text))
		except ValueError:
			self.movement_step=0
			self.motion_step.setText('')

	def change_motion_position(self):
		self.motion_position.setText(str(self.value_assign.t))

	def thread_complete(self):
		print('Thread complete')
			
	def stage_relative_move(self,direction):
		def inner_function():
			#self.threadpool.waitForDone()
			worker = Worker(self.stage_relative_move_raw(direction)) # Any other args, kwargs are passed to the run function
			#worker.signals.result.connect(self.print_output)
			#worker.signals.finished.connect(self.thread_complete)
			#worker.signals.progress.connect(self.progress_fn)
			#example:https://www.learnpyqt.com/courses/concurrent-execution/multithreading-pyqt-applications-qthreadpool/
			
			self.threadpool.start(worker)
		return inner_function

	def stage_relative_move_raw(self,direction):
		def inner_function(progress_callback):
			self.m.rel_move(self.stage_id,direction*self.movement_step)
		return inner_function


# Subclass QMainWindow to customise your application's main window
class MainWindow(QMainWindow):

	def __init__(self, *args, **kwargs):
		super(MainWindow, self).__init__(*args, **kwargs)
		
		self.widgets_to_add=[]
		self.setWindowTitle("Laser Driver App")
		self.m=MotionStageController()
		self.twodscan=TwoDScan(self.m)
		
		
		#label = QLabel('Relative movement')
		row_layout_1=_Motion_Stage_Row(stage_label='Laser	', stage_id = self.m.devices['L'], motion_stage_controller=self.m )
		row_layout_2=_Motion_Stage_Row(stage_label='Horizontal', stage_id = self.m.devices['H'], motion_stage_controller=self.m)
		row_layout_3=_Motion_Stage_Row(stage_label='Vertical	', stage_id = self.m.devices['V'], motion_stage_controller=self.m)
		#self.widgets_to_add.append(label)
		self.widgets_to_add.append(row_layout_1)
		self.widgets_to_add.append(row_layout_2)
		self.widgets_to_add.append(row_layout_3)
		self.monitor_rows=self.widgets_to_add[-3:]
		
		button1 = QPushButton('Stop Motion')
		button1.clicked.connect(self.stopall)
		button1.setFixedWidth(200)
		button1.setFixedHeight(70)
		self.widgets_to_add.append(button1)

		self.threadpool = QThreadPool()
		constant_worker=Worker(self.monitor_positions_constantly)
		self.threadpool.start(constant_worker)
		
		self.set_layout()
		
		
	def set_layout(self):
		layout=QGridLayout()
		for i,item in enumerate(self.widgets_to_add):
			layout.addWidget(item,i,0,1,1,Qt.AlignCenter)
			
		layout.addWidget(self.twodscan,0,1,4,1,Qt.AlignCenter)
		
		centralWidget = QWidget(self)
		self.setCentralWidget(centralWidget)
		centralWidget.setLayout(layout)
		
		self.setGeometry(50,50,1000,500)
		self.setWindowTitle("Laser Driver")

	def monitor_positions_constantly(self,progress_callback):
		while True:
			for row in self.monitor_rows:
				time.sleep(0.05)
				pos,upos=self.m.get_position(row.stage_id)
				row.motion_position.setText(str(pos))
	def stopall(self):
		self.m.stopall()
		self.twodscan.stop()
				

app = QApplication(sys.argv)

window = MainWindow()
window.show()

app.exec_()