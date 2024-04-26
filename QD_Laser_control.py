import os
import pyvisa as visa

class QD_Laser():
    def __init__(self):
        rm=visa.ResourceManager()
        self.data_dict={}
        self.device=rm.open_resource("ASRL7::INSTR")

    # The laser tends to give not up-to-date values shortly after changes, hence a loop was implemented
    def query_loop(self, task):
        for i in range(0,10):
            query = self.device.query(str(task)+'?')
        return query

    def set_gate(self, value=None):
        if not value:
            print('Set gate value= in range [200, 2050] mV')
        elif not (value>=200 and value<=2050):
            print('Gate value out of range [200, 2050] mV')
        else:
            self.device.write('VGG='+str(int(value)).zfill(4))
        
    def get_gate(self):
        self.query_loop('VGG')
        return self.device.query('VGG?')[:4]
    
    def set_bias(self, value=None):
        if not value:
            print('Set bias current value= in range [0.0, 100.0] mA')
        elif not (value>=0 and value<=100):
            print('Bias current value out of range [0.0, 100.0] mA')
        else:
            self.device.write('BIA='+str(int(value*10)).zfill(4))
        
    def get_bias(self):
        self.query_loop('BIA')
        return self.device.query('BIA?')[:4]

    def set_temp(self, value=None):
        if not value:
            print(u'Set temperature value= in range [10.00, 45.00]\N{DEGREE SIGN}C')
        elif not (value>=10 and value<=45):
            print(u'Temperature value out of range [10.00, 45.00]\N{DEGREE SIGN}C')
        else:
            self.device.write('TMP='+str(int(value*100)).zfill(4))
        
    def get_temp(self):
        self.query_loop('TMP')
        return self.device.query('TMP?')[:4]

    def set_temp_alarm(self, value=None):
        if not value:
            print(u'Set temperature alarm value= in range [35.00, 45.00]\N{DEGREE SIGN}C')
        elif not (value>=35 and value<=45):
            print(u'Temperature alarm value out of range [35.00, 45.00]\N{DEGREE SIGN}C')
        else:
            self.device.write('AT3='+str(int(value*100)).zfill(4))
        
    def get_temp_alarm(self):
        self.query_loop('AT3')
        return self.device.query('AT3?')[:4]

    def trigger_on(self):
        self.device.write('CKS=2')
        
    def trigger_off(self):
        self.device.write('CKS=3')
    
    def trigger_external(self, source=None):  
        if not (source==1 or source==2):
            if not source:
                source=0
                print('External trigger set to CLK1, for CLK2 provide source=2')
            else:
                print('Invalid external source, for CLK1 provide source=1, for CLK2 provide source=2')
        else:
            source=int(source)-1
        self.device.write('CKS='+str(source))

    def trigger_status(self):
        self.query_loop('CKS')
        trig_name = ['Ext CLK1', 'Ext CLK2', 'Internal OSC', 'Stop']
        trig_val = self.device.query('CKS?')[0]
        return trig_name[int(trig_val)]

    def tec_off(self):
        self.device.write('TEC=0')
        
    def tec_on(self):
        self.device.write('TEC=1')
        
    def tec_status(self):
        # return int(self.query_loop('TEC')[0])
        return int(self.query_loop('TEC'))
        
    def current_off(self):
        self.device.write('LDD=0')
        
    def current_on(self):
        self.device.write('LDD=1')
        
    def current_status(self):
        return int(self.query_loop('LDD')[0])

    def monitor_temp(self):
        return self.query_loop('TEM')[:4]
        
    def monitor_gate(self):
        return self.query_loop('VGM')[1:5]
        
    def monitor_bias(self):
        return self.query_loop('BIM')[:4]
        
    def monitor_3vsup(self):
        return self.query_loop('V3M')[:4]
        
    def monitor_5vsup(self):
        return self.query_loop('V5M')[:4]
    
    def monitor_alarm(self):
        return self.query_loop('ALM')[:3]
    
    def control_report(self):
        status_name = ['OFF', 'ON']
        report = []
        report.append(u'Temp setting   '+str(int(self.get_temp())/100)+'\N{DEGREE SIGN}C')
        report.append(u'Temp alarm     '+str(int(self.get_temp_alarm())/100)+'\N{DEGREE SIGN}C')
        report.append('Gate setting   '+str(int(self.get_gate()))+' mV')
        report.append('Bias setting   '+str(int(self.get_bias())/10)+' mA')
        report.append('Trigger set    '+str(self.trigger_status()))
        report.append('TEC  status:   '+status_name[int(self.tec_status())])
        report.append('Bias status:   '+status_name[int(self.current_status())])
        return report
    
    def monitor_report(self):
        alarm_status = ['OK', 'ALARM']
        report = []
        report.append(u'LD temperature '+str(int(self.monitor_temp())/100)+'\N{DEGREE SIGN}C')
        report.append('LD temp alarm  '+alarm_status[int(self.monitor_alarm()[0])])
        report.append('Gate voltage  -'+str(int(self.monitor_gate()))+' mV')
        report.append('Bias current   '+str(int(self.monitor_bias())/10)+' mA')
        report.append('+3.3V supply   '+str(int(self.monitor_3vsup())/1000)+' V')
        report.append('+3.3V alarm    '+alarm_status[int(self.monitor_alarm()[1])])
        report.append('+5V supply     '+str(int(self.monitor_5vsup())/1000)+' V')
        report.append('+5V alarm      '+alarm_status[int(self.monitor_alarm()[2])])
        return report

    def show_report(self):
        print('\nControl report')
        c_report = self.control_report()
        for line in c_report:
            print(line)
        print('\nMonitor report')
        m_report = self.monitor_report()
        for line in m_report:
            print(line)

if __name__=='__main__':
    qd=QD_Laser()
