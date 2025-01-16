from .runner import Runner, get_ser
from actor import *
from extractor import *
from predictor import *
from parser import *
from feature_extractor import *
from multiprocessing import Process, Queue
import re
import argparse
import yaml

def get_wdm(fn):
    with open(fn, 'r') as file:
       pattern = r"\[(\/dev\/cdc-wdm\d+)\]" 
       content = file.read()
       matches = re.findall(pattern, content)

def create_runner(dev, queue):
    rrc_ota_parser = RRC_OTA_Parser()
    lte_ss_parser = Lte_Signal_Strength_Parser()
    nr_ss_parser = NR_Signal_Strength_Parser()

    ho_extractor = HO_Extractor()
    ho_extractor.set_source_parser(rrc_ota_parser)

    mr_extractor = MR_Extractor()
    mr_extractor.set_source_parser(rrc_ota_parser)

    lte_ss_extractor = Lte_Signal_Strength_Extractor()
    lte_ss_extractor.set_source_parser(lte_ss_parser)

    nr_ss_extractor = NR_Signal_Strength_Extractor()
    nr_ss_extractor.set_source_parser(nr_ss_parser)

    feature_extractor = FeatureExtractor(sample_interval_sec=0.1, sample_length_sec = 3)
    feature_extractor.add_parser(rrc_ota_parser)
    feature_extractor.add_parser(lte_ss_parser)
    feature_extractor.add_parser(nr_ss_parser)
    feature_extractor.add_extractor(ho_extractor)
    feature_extractor.add_extractor(mr_extractor)
    feature_extractor.add_extractor(lte_ss_extractor)
    feature_extractor.add_extractor(nr_ss_extractor)
    


    feature_extractor.set_data_order(
        [
            "LTE_HO",
            "MN_HO",
            "SN_setup",
            "SN_Rel",
            "SN_HO",
            "Conn_Req",
            "RLF",
            "SCG_RLF",
            "eventA1",
            "eventA2",
            "E-UTRAN-eventA3",
            "eventA5",
            "eventA6",
            "NR-eventA3",
            "eventB1-NR-r15",
            "reportCGI",
            "reportStrongestCells",
            "others",
            "nr_best_rsrq",
            "nr_best_rsrp",
            "lte_best_rsrq",
            "lte_best_rsrp",
            "current_nr_rsrq",
            "current_nr_rsrp",
            "current_lte_rsrq",
            "current_lte_rsrp",
            "scell1_lte_rsrq",
            "scell1_lte_rsrp",
            "scell2_lte_rsrq",
            "scell2_lte_rsrp",
            "scell3_lte_rsrq",
            "scell3_lte_rsrp",
            "lte_phy_EARFCN",
            "lte_phy_Number_of_Neighbor_Cells",
            "nr_phy_Num_Cells",
        ]
    )
    actor = DBL_Actor(queue, dev, feature_extractor)
    predictor = RLF_Xgboost_Predictor()
    runner = Runner(
        ser=get_ser('',dev),
        predictor=predictor,
        feature_extractor=feature_extractor,
        predict_interval = 0.1
    )
    return runner

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config_file', default='config.yml', help="Config file (yaml)")
    args = parser.parse_args()
    with open(args.config_file,'r') as f:
        config = yaml.safe_load(f)
    args.devs = devs = ['qc01', 'qc02']
    
    q = Queue()
    runner1, runner2 = create_runner(devs[0], q), create_runner(devs[1], q)
    
    # lte_phy_EARFCN
    while True:
        outs_info = {devs[0]:(False, None), devs[1]:(False, None)}
        while not q.empty():
            e = q.get()
            outs_info[e[0]] = (e[1], e[2])
        
        if outs_info[devs[0]][0] == False and outs_info[devs[0]][0] == False:
            continue
        
        if outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == False:
            pass
        elif outs_info[devs[0]][0] == False and outs_info[devs[1]][0] == True:
            pass
        elif outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == True:
            pass