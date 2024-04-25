import os
class Laser_IR():
    def __init__(self):
        self.executable='PaLaser\\PaLaser.exe'

    def turn_off(self):
        os.system(self.executable+' -off')
        
    def turn_on(self,freq=50):
        os.system(self.executable+' -f '+ str(freq))
        
    def set_dac(self, dac_val=1320): #40%=1320
        os.system(self.executable+' -p '+str(dac_val))


if __name__=='__main__':
    l=Laser_IR()
    
    
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