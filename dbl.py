from runner import Runner, get_ser
from actor import *
from extractor import *
from predictor import *
from parser import *
from feature_extractor import *
from multiprocessing import Process, Queue
import re
import argparse
import yaml
import subprocess
import os
import random

GLOBAL_CONFIG = None
DEVICE_INFO = None

ALL_LTE_BAND_CANDIDATE = {1, 3, 7, 8}

def load_config(config_file):
    global GLOBAL_CONFIG
    with open(config_file, 'r') as f:
        GLOBAL_CONFIG = yaml.safe_load(f)

def setup_modem(dev):
    global GLOBAL_CONFIG
    process = subprocess.Popen(
        [
            os.path.join(GLOBAL_CONFIG['PATH_UTILS'], 'dial-qmi.sh'),
            '-i',
            dev
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate()
    
    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())
    
    with open(os.path.join(GLOBAL_CONFIG['PATH_TEMP_DIR'], f'temp-nas_{dev}'), 'r') as f:
        pattern = r"\[(\/dev\/cdc-wdm\d+)\]"
        content = f.read()
        matches = re.findall(pattern, content)[0]
        wdm = matches
        pattern = r"CID:\s*'(\d+)'"
        matches = re.findall(pattern, content)[0]
        cid = matches
    
    
    subprocess.Popen(
        ' '.join([
            os.path.join(GLOBAL_CONFIG['PATH_UTILS'], 'band-setting.sh'), 
            '-i', 
            dev, 
            '-l', 
            ':'.join([str(i) for i in [1,3,7,8]])
        ]), 
        shell=True
    )
    stdout, stderr = process.communicate()

    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())
        
    return wdm, cid

def change_band(dev):
    global GLOBAL_CONFIG, DEVICE_INFO
    
    band_candidate = ALL_LTE_BAND_CANDIDATE.copy()
    for k, v in DEVICE_INFO:
        band_candidate = band_candidate - {v['band']}
    
    band = random.choice(list(band_candidate))
    print(band)
    
    subprocess.Popen(
        ' '.join([
            os.path.join(GLOBAL_CONFIG['PATH_UTILS'], 'band-setting.sh'), 
            '-i', 
            dev, 
            '-l', 
            str(band)
        ]
    ), shell=True)
    print(f"""Change band from {DEVICE_INFO[dev]['band']} to {band}""")
    DEVICE_INFO[dev]['band'] = band


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

    feature_extractor = FeatureExtractor(
        sample_interval_sec=0.1, sample_length_sec=3)
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
    predictor = RLF_Xgboost_Predictor(GLOBAL_CONFIG['MODEL_PATH'])
    runner = Runner(
        ser=get_ser('', dev),
        predictor=predictor,
        feature_extractor=feature_extractor,
        predict_interval=0.1,
        actor=actor
    )
    return runner


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-c', '--config_file',
                        default='config.yml', help="Config file (yaml)")
    args = parser.parse_args()
    
    load_config(args.config_file)

    devs = GLOBAL_CONFIG['Device']

    if (len(devs) != 2):
        raise Exception("DBL need at least 2 device")
    
    # Setup modem
    DEVICE_INFO = {}
    for dev in devs:
        wdm, cid = setup_modem(dev)
        DEVICE_INFO[dev] = {'wdm': wdm, 'cid': cid, 'band': [1,3,7,8]}
    band_setting_timestamp = time.time() - 10
    
    try:
        q = Queue()
        runner1, runner2 = create_runner(devs[0], q), create_runner(devs[1], q)
        
        p1 = Process(target=runner1.run)     
        p2 = Process(target=runner2.run)
        p1.start()
        p2.start()

        # lte_phy_EARFCN
        e = None
        outs_info = {devs[0]: [False, None], devs[1]: [False, None]}
        while True:
            outs_info[devs[0]][0] = False
            outs_info[devs[1]][0] = False
            
            while not q.empty():
                e = q.get()

            if time.time() - band_setting_timestamp < GLOBAL_CONFIG['SLEEP_TIME'] or e is None:
                time.sleep(0.1)
                continue
            
            outs_info[e[0]] = [e[1] > 0.5, e[2]]
            print(outs_info)

            if outs_info[devs[0]][0] == False and outs_info[devs[0]][0] == False:
                continue
            
            band_setting_timestamp = time.time()
            
            if outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == False:
                change_band(devs[0])
            elif outs_info[devs[0]][0] == False and outs_info[devs[1]][0] == True:
                change_band(devs[1])
            elif outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == True:
                # change_band(devs[0])
                pass
    
    except KeyboardInterrupt:
        print('Main process received KeyboardInterrupt')
        p1.join()
        p2.join()
        time.sleep(1)
        print("Process killed, closed.")()
