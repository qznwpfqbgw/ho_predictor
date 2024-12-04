from parser import Parser
from datetime import datetime as dt
# Get HO events
class RRC_OTA_Parser(Parser):
    
    def __init__(self):
        super().__init__()
        self.type_id = ["LTE_RRC_OTA_Packet", "5G_NR_RRC_OTA_Packet"]
        self.RRC_DICT = {}
        self.type_list = [
            '"rrcConnectionRelease"',
            '"lte-rrc.rrcConnectionRequest_element"',
            '"lte-rrc.targetPhysCellId"',
            'dl-CarrierFreq',
            '"lte-rrc.t304"',
            '"nr-rrc.physCellId"',
            '"nr-rrc.t304"',
            '"dualConnectivityPHR: setup (1)"',
            '"rrcConnectionReestablishmentRequest"',
            'physCellId', 
            'reestablishmentCause',
            '"scgFailureInformationNR-r15"',
            'failureType-r15',
            # Use for find event
            '"lte-rrc.measurementReport_element"',
            '"nr-rrc.measurementReport_element"',
            'measId',
            '"lte-rrc.MeasObjectToAddMod_element"',
            '"nr-rrc.MeasObjectToAddMod_element"',
            'measObjectId', 
            'measObject', 
            'carrierFreq', 
            'carrierFreq-r15',
            'ssbFrequency',
            '"lte-rrc.ReportConfigToAddMod_element"',
            'lte-reportConfigId',
            'lte-eventId',
            '"nr-rrc.ReportConfigToAddMod_element"',
            'nr-reportConfigId',    
            'nr-eventId',
            '"lte-rrc.measIdToRemoveList"',
            '"lte-rrc.MeasIdToAddMod_element"',
            '"nr-rrc.MeasIdToAddMod_element"'
        ]  
        # rrc cloumns
        self.columns = [
            "rrcConnectionRelease",
            "rrcConnectionRequest",
            "lte_targetPhysCellId", # Handover target.
            "dl-CarrierFreq",
            "lte-rrc.t304",
            "nr_physCellId", # NR measured target PCI
            "nr-rrc.t304",
            "dualConnectivityPHR: setup (1)",
            "rrcConnectionReestablishmentRequest",
            "physCellId", # Target PCI for rrcConnectionReestablishmentRequest.
            "reestablishmentCause", # ReestablishmentCause for rrcConnectionReestablishmentRequest.
            "scgFailureInformationNR-r15",
            "failureType-r15", # Failure cause of scgfailure.
            # Use for find event
            "lte-measurementReport",
            "nr-measurementReport",
            "measId",
            "lte-MeasObjectToAddMod",
            "nr-MeasObjectToAddMod",
            "measObjectId", 
            "measObject", # measObjectEUTRA (0) OR measObjectNR-r15 (5)
            "carrierFreq", # For EUTRA
            "carrierFreq-r15", # For measObjectNR-r15
            "ssbFrequency", # For measObjectNR
            "lte-ReportConfigToAddMod",
            "lte-reportConfigId",
            "lte-eventId",
            "nr-ReportConfigToAddMod",
            "nr-reportConfigId",
            "nr-eventId",
            "lte-measIdToRemoveList",
            "lte-MeasIdToAddMod",## (MeasId & measObjectId & reportConfigId)
            "nr-MeasIdToAddMod",
        ]
        for col in ['PCI', 'time', 'Freq'] + self.columns:
            self.RRC_DICT[col] = []
        
    def reset(self):
        for col in ['PCI', 'time', 'Freq'] + self.columns:
            self.RRC_DICT[col] = []

    def catch_info(self, msg_dict):
        easy_dict = {}
        easy_dict["PCI"], easy_dict["time"], easy_dict["Freq"] = msg_dict['Physical Cell ID'], msg_dict['timestamp'], msg_dict['Freq']
        readlines = msg_dict['Msg'].split('\n')
        rrc_info_dict = self.read_rrc_msg_content(readlines)
        for key in rrc_info_dict:
            easy_dict[key] = rrc_info_dict[key] 
        easy_dict = {k:[str(v)] for k,v in easy_dict.items()}
        return easy_dict

    @staticmethod
    def get_text(l, NAME): # Given l, return XXXX if NAME in l, else error. Format "NAME: XXXX".
        a = l.index('"' + NAME)
        k = len(NAME)+3
        b = l.index("\"", a+1)
        return l[a+k:b]
    
    @staticmethod
    def multi_output_write(type_code, c, type, l, sep='@'):
        if type_code[c] == "0": 
            return RRC_OTA_Parser.get_text(l, type)
        else: 
            return type_code[c] + sep + RRC_OTA_Parser.get_text(l, type)
            
        
    def read_rrc_msg_content(self, readlines: list):

        type_code = ["0"] * len(self.type_list)
        l, count = readlines[0], 0
        
        def passlines(n):
            nonlocal count, l, readlines
            count += n
            l = readlines[count]
            
        while count < len(readlines):
            l = readlines[count]
            next = 0
            for i, type in enumerate(self.type_list):
                if next != 0:
                    next -= 1
                    continue

                c = i
                if type in l:
                    if type == '"lte-rrc.targetPhysCellId"':
                        type_code[c] = RRC_OTA_Parser.get_text(l, 'targetPhysCellId')
                        c += 1; passlines(2)
                        if '"lte-rrc.t304"' in l:
                            type_code[c] = 'intrafreq'
                            c += 1; type_code[c] = "1"
                            next = 2
                        else:
                            passlines(1)
                            type_code[c] = RRC_OTA_Parser.get_text(l, 'dl-CarrierFreq')
                            next = 1

                    elif type == '"nr-rrc.physCellId"':
                        type_code[c] = RRC_OTA_Parser.get_text(l, 'physCellId')

                    elif type == '"rrcConnectionReestablishmentRequest"':
                        type_code[c] = "1"
                        c += 1; passlines(6)
                        type_code[c] = RRC_OTA_Parser.get_text(l, 'physCellId')
                        c += 1; passlines(4)
                        type_code[c] = RRC_OTA_Parser.get_text(l, 'reestablishmentCause')
                        next = 2

                    elif type == '"scgFailureInformationNR-r15"':
                        type_code[c] = "1"
                        c += 1; passlines(13)
                        type_code[c] = RRC_OTA_Parser.get_text(l, 'failureType-r15')
                        next = 1
                    
                    elif type == '"lte-rrc.measurementReport_element"':
                        type_code[c] = "1"
                        c+=2; passlines(10)
                        type_code[c] = RRC_OTA_Parser.get_text(l, "measId")
                        next = 2
                        
                    elif type == '"nr-rrc.measurementReport_element"':
                        type_code[c] = '1'
                        c+=1; passlines(9)
                        try: type_code[c] = RRC_OTA_Parser.get_text(l, "measId")
                        except: type_code[c] = "none"
                        next = 1
                        
                    elif type == '"lte-rrc.MeasObjectToAddMod_element"':
                        type_code[c] = "1"
                        c+=2; passlines(1)
                        type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'measObjectId', l)
                        c+=1
                        while l:
                            passlines(1)
                            if '"lte-rrc.measObject"' in l:
                                type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'measObject', l)
                                obj = RRC_OTA_Parser.get_text(l, 'measObject')
                                passlines(9)
                                if obj == 'measObjectEUTRA (0)':
                                    c+=1
                                    type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'carrierFreq', l)
                                elif obj == 'measObjectNR-r15 (5)':
                                    c+=2
                                    type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'carrierFreq-r15', l)
                                next = 6
                                break
                    
                    elif type == '"nr-rrc.MeasObjectToAddMod_element"':
                        type_code[c] = "1"
                        c+=1; passlines(1)
                        type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'measObjectId', l)
                        c+=1
                        while l:
                            passlines(1)
                            if '"nr-rrc.measObject"' in l:
                                type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'measObject', l)
                                obj = RRC_OTA_Parser.get_text(l, 'measObject')
                                passlines(18)
                                if obj == 'measObjectNR (0)':
                                    c+=3
                                    type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'ssbFrequency', l)
                                next=5
                                break
                        
                    elif type == '"lte-rrc.ReportConfigToAddMod_element"':
                        type_code[c] = "1"
                        c+=1; passlines(1)
                        type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'reportConfigId', l)
                        c+=1; passlines(6)
                        triggerType = RRC_OTA_Parser.get_text(l, 'triggerType')
                        if triggerType == "event (0)":
                            try: 
                                passlines(4)
                                eventId = RRC_OTA_Parser.get_text(l, 'eventId')
                            except: # eventId B1
                                passlines(2)
                                eventId = RRC_OTA_Parser.get_text(l, 'eventId')
                            type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'eventId', l)
                        elif triggerType == "periodical (1)":
                            passlines(3)
                            type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'purpose', l)
                        next = 2
                    
                    elif type == '"nr-rrc.ReportConfigToAddMod_element"':
                        type_code[c] = "1"
                        c+=1; passlines(1)
                        type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'reportConfigId', l)
                        c+=1; passlines(14)
                        type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'eventId', l)
                        next = 2
                        
                    elif type == '"lte-rrc.measIdToRemoveList"':
                        item_num = RRC_OTA_Parser.get_text(l, 'measIdToRemoveList').split(' ')[0]
                        item_num = int(item_num)
                        for n in range(item_num):
                            if n == 0: 
                                passlines(2)
                                type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'MeasId', l)
                            else:
                                passlines(3)
                                type_code[c] = RRC_OTA_Parser.multi_output_write(type_code, c, 'MeasId', l)
                    
                    elif type == '"lte-rrc.MeasIdToAddMod_element"' or type == '"nr-rrc.MeasIdToAddMod_element"':
                        passlines(1); measId = RRC_OTA_Parser.get_text(l, 'measId')
                        passlines(1); measObjectId = RRC_OTA_Parser.get_text(l, 'measObjectId')
                        passlines(1); reportConfigId = RRC_OTA_Parser.get_text(l, 'reportConfigId')
                        if type_code[c] == "0": 
                            type_code[c] = f'({measId}&{measObjectId}&{reportConfigId})' 
                        else: 
                            type_code[c] = type_code[c] + '@' + f'({measId}&{measObjectId}&{reportConfigId})'
                    
                    elif type not in ['physCellId', 'dl-CarrierFreq',"measObjectId", "measObject", "reportConfigId", "measId","carrierFreq"]:
                        type_code[c] = "1"

            count += 1

        rrc_info_dict = {}
        for type, value in zip(self.columns, type_code):
            rrc_info_dict[type] = value

        return rrc_info_dict
        
    def parse(self, msg):
        if msg.type_id == "LTE_RRC_OTA_Packet":
            msg_dict = dict(msg.data.decode())
            return self.catch_info(msg_dict)
    