from historiansim.config.schema import LoopConfig,ChannelConfig

def plant_loops():return [LoopConfig(name='SIC-1500',pv_source='SI-1500',mv_tag='DRIVE-1500',kc=.03,ti=30.,sp=8.,action='reverse')]
def plant_channels():return {'T_amb':ChannelConfig(mean=20.,units='degC',description='Ambient air temperature',sigma=.05,tau_s=1800.)}
