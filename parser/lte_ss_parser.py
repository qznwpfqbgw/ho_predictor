from .parser import Parser
from bs4 import BeautifulSoup
import io
from itertools import chain

class Lte_Signal_Strength_Parser(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.type_id = ['LTE_PHY_Connected_Mode_Intra_Freq_Meas']
        self.default_data = {
            "PCI": 0,
            "RSRP(dBm)": -200,
            "RSRQ(dB)": -200,
            "Serving Cell Index": "",
            "EARFCN": 0,
            "Number of Neighbor Cells": 0,
            "Number of Detected Cells": 0,
            "PCI1": 0,
            "RSRP1": -200,
            "RSRQ1": -200,
            "PCI2": 0,
            "RSRP2": -200,
            "RSRQ2": -200,
            "PCI3": 0,
            "RSRP3": -200,
            "RSRQ3": -200,
            "PCI4": 0,
            "RSRP4": -200,
            "RSRQ4": -200,
            "PCI5": 0,
            "RSRP5": -200,
            "RSRQ5": -200,
            "PCI6": 0,
            "RSRP6": -200,
            "RSRQ6": -200,
            "PCI7": 0,
            "RSRP7": -200,
            "RSRQ7": -200,
            "PCI8": 0,
            "RSRP8": -200,
            "RSRQ8": -200,
            "PCI9": 0,
            "RSRP9": -200,
            "RSRQ9": -200,
            "PCI10": 0,
            "RSRP10": -200,
            "RSRQ10": -200,
            "PCI11": 0,
            "RSRP11": -200,
            "RSRQ11": -200,
            "PCI12": 0,
            "RSRP12": -200,
            "RSRQ12": -200,
            "PCI13": 0,
            "RSRP13": -200,
            "RSRQ13": -200,
            "PCI14": 0,
            "RSRP14": -200,
            "RSRQ14": -200,
        }
        self.current_data = self.default_data.copy()
        
    def parse(self, msg):
        msg_io = io.StringIO(msg.data.decode_xml())
        l = msg_io.readline()
        out = self.default_data.copy()
        
        if r"<dm_log_packet>" in l:
            soup = BeautifulSoup(l, 'html.parser')
            try:
                pci = int(soup.find(key="Serving Physical Cell ID").get_text()) ## This is current serving cell PCI.
            except:
                pci = 0
            serving_cell = soup.find(key="Serving Cell Index").get_text()
            earfcn = int(soup.find(key="E-ARFCN").get_text())
            n_nei_c = int(soup.find(key="Number of Neighbor Cells").get_text())
            n_det_c = int(soup.find(key="Number of Detected Cells").get_text())
            rsrps = [float(rsrp.get_text()) for rsrp in soup.findAll(key="RSRP(dBm)")]
            rsrqs = [float(rsrq.get_text()) for rsrq in soup.findAll(key="RSRQ(dB)")]
            PCIs = [int(pci.get_text()) for pci in soup.findAll(key="Physical Cell ID")]
            if int(n_det_c) != 0:
                PCIs = PCIs[:-int(n_det_c)]
            A = [[PCIs[i], rsrps[i+1], rsrqs[i+1]] for i in range(len(PCIs))] ## Information of neighbor cell
            A = list(chain.from_iterable(A))
            A = [pci, rsrps[0], rsrqs[0], serving_cell, earfcn, n_nei_c, n_det_c] + A
            if len(A) < len(self.default_data):
                for _ in range(len(self.default_data) - len(A)):
                    A.append(-200)
            cnt = 0
            for k, _ in self.default_data.items():
                self.current_data[k] = [A[cnt]]
                cnt += 1
        return self.current_data
                