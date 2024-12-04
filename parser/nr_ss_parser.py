from .parser import Parser
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import io
from itertools import chain


class NR_Signal_Strength_Parser(Parser):
    def __init__(self) -> None:
        super().__init__()
        self.type_id = ["5G_NR_ML1_Searcher_Measurement_Database_Update_Ext"]
        self.default_data = {
            "SSB Periodicity Serv Cell": 0,
            "Frequency Offset": 0,
            "Timing Offset": 0,
            "Raster ARFCN": 0,
            "Num Cells": 0,
            "Serving Cell Index": 0,
            "Serving Cell PCI": 0,
            "PCI0": 0,
            "RSRP0": -200,
            "RSRQ0": -200,
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
            "PCI15": 0,
            "RSRP15": -200,
            "RSRQ15": -200,
        }
        self.current_data = self.default_data.copy()

    def parse(self, msg):
        msg = msg.data.decode_xml()
        tree = ET.fromstring(msg)
        msg_io = io.StringIO(msg)
        
        # num_layer = tree.find("pair[@key='Num Layers']")
        # if num_layer is not None:
        #     num_layer = num_layer.text
        #     if not num_layer.isnumeric():
        #         num_layer = int(num_layer)
        # num_layer = 0

        ssb_periodicity = tree.find("pair[@key='SSB Periodicity Serv Cell']").text
        if not ssb_periodicity.isnumeric():
            ssb_periodicity = 0
        else:
            ssb_periodicity = int(ssb_periodicity)

        freq_offset = float(tree.find("pair[@key='Frequency Offset']").text.split(" ")[0])
        time_offset = float(tree.find("pair[@key='Timing Offset']").text)
        msg_io = io.StringIO(msg)
        l = msg_io.readline()
        
        if r"<dm_log_packet>" in l:
            soup = BeautifulSoup(l, "html.parser")
            arfcn = int(soup.find(key="Raster ARFCN").get_text())

            num_cells = int(soup.find(key="Num Cells").get_text())
            serving_cell_idex = int(soup.find(key="Serving Cell Index").get_text())
            serving_cell_pci = int(soup.find(key="Serving Cell PCI").get_text())
            pcis = [int(pci.get_text()) for pci in soup.findAll(key="PCI")]
            rsrps = [float(rsrp.get_text()) for rsrp in soup.findAll(key="Cell Quality Rsrp")]
            rsrqs = [float(rsrq.get_text()) for rsrq in soup.findAll(key="Cell Quality Rsrq")]
            A = []
            for i in range(int(num_cells)):
                A.append(pcis[i])
                A.append(rsrps[i])
                A.append(rsrqs[i])

            A = [
                ssb_periodicity,
                freq_offset,
                time_offset,
                arfcn,
                num_cells,
                serving_cell_idex,
                serving_cell_pci,
            ] + A
            if len(A) < len(self.default_data):
                for _ in range(len(self.default_data) - len(A)):
                    A.append(0)
            cnt = 0
            for k, _ in self.default_data.items():
                self.current_data[k] = [A[cnt]]
                cnt += 1
        return self.current_data
