from .extractor import *
from collections import namedtuple

class HO_Extractor(Extractor):
    def __init__(self) -> None:
        super().__init__()
        self.default_output = {
            "LTE_HO": 0,
            "MN_HO": 0,
            "SN_setup": 0,
            "SN_Rel": 0,
            "SN_HO": 0,
            "Conn_Req": 0,
            "RLF": 0,
            "SCG_RLF": 0,
        }
        
    def parse_mi_ho(self, df):
        HO = namedtuple('HO','start', defaults=(None))

        D = {
            'LTE_HO': [], # LTE -> newLTE
            'MN_HO': [], # LTE + NR -> newLTE + NR
            'SN_setup': [], # LTE -> LTE + NR => NR setup
            'SN_Rel': [], # LTE + NR -> LTE
            'SN_HO': [], # LTE + NR -> LTE + newNR
            'Conn_Req': [],
            'RLF': [],
            'SCG_RLF': [],
            }
        for i in range(len(df['rrcConnectionRelease'])):
            t = df["time"][i]
            
            if df["lte-rrc.t304"][i] == '1':
                serv_cell, target_cell = df["PCI"][i], df['lte_targetPhysCellId'][i]
                serv_freq, target_freq = df["Freq"][i], df['dl-CarrierFreq'][i]
                
                if df["nr-rrc.t304"][i] == '1' and df["dualConnectivityPHR: setup (1)"][i] == '1':

                    if serv_cell == target_cell and serv_freq == target_freq:
                        D['SN_setup'].append(HO(start=t))
                        # print(1, t, f"Serving Cell: {serv_cell}->{target_cell}")  
                    else:    
                        D['MN_HO'].append(HO(start=t))
                else:
                    if serv_cell == target_cell and serv_freq == target_freq:
                        D['SN_Rel'].append(HO(start=t))
                    else:
                        D['LTE_HO'].append(HO(start=t))

            if df["nr-rrc.t304"][i] == '1' and not df["dualConnectivityPHR: setup (1)"][i] == '1':
                D['SN_HO'].append(HO(start=t))

            if df["rrcConnectionReestablishmentRequest"][i] == '1':  
                D['RLF'].append(HO(start=t))
                
            if df["scgFailureInformationNR-r15"][i] == '1':
                D['SCG_RLF'].append(HO(start=t))
                
            if df["rrcConnectionRequest"].iloc[i] == '1':
                D['Conn_Req'].append(HO(start=t))
        
        return D
    
    def extract(self, df) -> dict:
        HOs = self.parse_mi_ho(df)
        out = {}
        
        for key in HOs:
            out[key] = 1 if len(HOs[key]) != 0 else 0
        return out