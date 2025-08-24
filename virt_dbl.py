from runner import Runner, get_ser
from actor import *
from extractor import *
from predictor import *
from parser import *
from feature_extractor import *
from multiprocessing import Process, Queue
from get_cell_info import get_cell_info, find_top_2_signal_band
import re
import yaml
import subprocess
import random
import datetime
import time
import numpy as np
import os
import mmap
from utils.band_conversion import *
from threading import Timer
import subprocess
import time
import signal
GLOBAL_CONFIG = None
DEVICE_INFO = None

ALL_LTE_BAND_CANDIDATE = set()

INIT_BAND = ["b1_b3_b7_b8", "b1_b3"]
PROCESS_LIST = []
DBL_LOG = None
class DelayedCommandExecutor:
    def __init__(self, cmd, time_to_exec):
        """
        初始化延遲執行器
        :param cmd: 要執行的命令 (list 或 string)
        :param time_to_exec: 延遲執行的時間 (秒)
        """
        self.cmd = cmd
        self.time_to_exec = time_to_exec

    def execute(self):
        """
        執行命令
        """
        # print(f"Executing command: {self.cmd}\r\n")
        p = subprocess.Popen(self.cmd, shell=True)

    def schedule(self):
        """
        排程延遲執行
        """
        # print(f"Command scheduled to run in {self.time_to_exec} seconds: {self.cmd}")
        timer = Timer(self.time_to_exec, self.execute)
        timer.start()



def load_config(config_file):
    global GLOBAL_CONFIG, ALL_LTE_BAND_CANDIDATE
    with open(config_file, "r") as f:
        GLOBAL_CONFIG = yaml.safe_load(f)
    ALL_LTE_BAND_CANDIDATE = set(GLOBAL_CONFIG["band_candidate"])


def create_log_dir(log_dir=None):
    if log_dir is None:
        now = dt.today()
        n = [
            now.year,
            now.month,
            now.day,
            now.hour,
            now.minute,
            now.second,
        ]
        n = [str(x).zfill(2) for x in n]
        n = "-".join(n[:3]) + "_" + "-".join(n[3:])
        os.umask(0)
        log_dir = os.path.join(os.path.dirname(__file__), "log", str(n))
    os.makedirs(log_dir, exist_ok=True)
    return log_dir

def set_band(dev, band):
    global GLOBAL_CONFIG, DEVICE_INFO
    DEVICE_INFO[dev]['band_info_buf'][0] = band_str_to_int(band)
    if GLOBAL_CONFIG["SIDE_EFFECT_S"] > 0:
        for interface in DEVICE_INFO[dev]['side_effect_interfaces']:
            subprocess.Popen(
                ' '.join([
                    "sudo",
                    'ip',
                    'netns',
                    'exec',
                    'NETEM',
                    'tc',
                    'qdisc',
                    'change',
                    'dev',
                    interface,
                    'parent',
                    "10:1",
                    'handle',
                    '20:',
                    'netem',
                    'loss',
                    '100%'
                ]),
                shell=True,
            )
            DelayedCommandExecutor(
                ' '.join([
                    "sudo",
                    'ip',
                    'netns',
                    'exec',
                    'NETEM',
                    'tc',
                    'qdisc',
                    'change',
                    'dev',
                    interface,
                    'parent',
                    "10:1",
                    'handle',
                    '20:',
                    'netem',
                    'loss',
                    '0%'
                ]),
                GLOBAL_CONFIG["SIDE_EFFECT_S"]
            ).schedule()

def setup_modem(dev: str, shm_file, init_band, side_effect_interfaces):
    global GLOBAL_CONFIG, DEVICE_INFO
    GLOBAL_CONFIG['shm'] = []
    if os.path.exists(shm_file):
        os.remove(shm_file)
    if not os.path.exists(shm_file):
        with open(shm_file, "wb") as f:
            f.write(b"\x00" * 9)  # 初始化 0
    fd = os.open(shm_file, os.O_RDWR)
    shm = mmap.mmap(fd, 9, access=mmap.ACCESS_WRITE)
    GLOBAL_CONFIG['shm'].append(shm)
    DEVICE_INFO[dev] = {}
    DEVICE_INFO[dev]['band_info_buf'] = np.frombuffer(shm, dtype=np.uint8, count=1, offset=8)
    DEVICE_INFO[dev]['band_info_buf'].flags.writeable = True
    DEVICE_INFO[dev]['band_info_buf'][0] = band_str_to_int(init_band)
    DEVICE_INFO[dev]['band'] = init_band
    DEVICE_INFO[dev]['side_effect_interfaces'] = side_effect_interfaces
    


def change_band(dev):
    global GLOBAL_CONFIG, DEVICE_INFO, ALL_LTE_BAND_CANDIDATE
    
    band_candidate = ALL_LTE_BAND_CANDIDATE.copy()
    band_candidate = band_candidate - {DEVICE_INFO[dev]['band']}

    band = random.choice(list(band_candidate))
    set_band(dev, band)
    print(f"""Change {dev} band from {DEVICE_INFO[dev]['band']} to {band}""")
    DEVICE_INFO[dev]["band"] = band


def change_follower_band(dev):
    global GLOBAL_CONFIG, DEVICE_INFO

    band = find_top_2_signal_band(
        get_cell_info(DEVICE_INFO[GLOBAL_CONFIG["Device"][0]]["wdm"], DEVICE_INFO[GLOBAL_CONFIG["Device"][0]]["cid"])
    )
    print(band)
    band = ','.join(band)
    

    subprocess.Popen(
        " ".join(
            [
                os.path.join(GLOBAL_CONFIG["PATH_UTILS"], "band-setting.sh"),
                "-i",
                dev,
                "-l",
                str(band),
            ]
        ),
        shell=True,
    )
    print(f"""Change {dev} band from {DEVICE_INFO[dev]['band']} to {band}""")
    DEVICE_INFO[dev]["band"] = band


def runner_proc(dev, queue):
    global GLOBAL_CONFIG
    rrc_ota_parser = RRC_OTA_Parser(dev=dev)
    lte_ss_parser = Lte_Signal_Strength_Parser(dev=dev)
    nr_ss_parser = NR_Signal_Strength_Parser(dev=dev)

    ho_extractor = HO_Extractor(dev=dev)
    ho_extractor.set_source_parser(rrc_ota_parser)

    mr_extractor = MR_Extractor(dev=dev)
    mr_extractor.set_source_parser(rrc_ota_parser)

    lte_ss_extractor = Lte_Signal_Strength_Extractor(dev=dev)
    lte_ss_extractor.set_source_parser(lte_ss_parser)

    nr_ss_extractor = NR_Signal_Strength_Extractor(dev=dev)
    nr_ss_extractor.set_source_parser(nr_ss_parser)

    feature_extractor = FeatureExtractor(sample_interval_sec=0.1, sample_length_sec=3)
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
    predictor = RLF_Xgboost_Predictor(GLOBAL_CONFIG["MODEL_PATH"], dev=dev)
    runner = Runner(
        ser=get_ser("", dev),
        predictor=predictor,
        feature_extractor=feature_extractor,
        predict_interval=0.1,
        actor=actor,
        log_dir=GLOBAL_CONFIG["LOG_DIR"],
    )
    runner.run()

def signal_handler(signum, frame):
    global PROCESS_LIST, DBL_LOG
    print("Signal handler called with signal:", signum)
    for process in PROCESS_LIST:
        process.terminate()
    DBL_LOG.close()
    time.sleep(1)
    print("Process killed, closed.")
    exit(0)

if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-c', '--config_file',
    #                     default='config.yml', help="Config file (yaml)")
    # args = parser.parse_args()

    # # load_config(args.config_file)

    load_config("config.yml")
    log_dir = create_log_dir()
    GLOBAL_CONFIG["LOG_DIR"] = log_dir

    devs_info = GLOBAL_CONFIG["Virt_Device"]
    devs = [i['device'] for i in devs_info]
    if len(devs) != 2:
        raise Exception("DBL need at least 2 device")

    # Setup modem
    DEVICE_INFO = {}
    for dev in devs_info:
        print(dev)
        setup_modem(dev['device'], dev['shm_file'], dev['init_band'], dev['side_effect_interfaces'])
    band_setting_timestamp = time.time() - 10

    f = os.path.join(GLOBAL_CONFIG["LOG_DIR"], "cmd_record.csv")
    DBL_LOG = open(f, "w")
    print("Timestamp,dev_0,band_0,dev_1,band_1", file=DBL_LOG, flush=True)
    DBL_LOG.write(
        ",".join(
            [
                datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                "0",
                str(DEVICE_INFO[devs[0]]["band"]),
                "0",
                str(DEVICE_INFO[devs[1]]["band"]),
            ]
        )
        + "\n"
    )

    try:
        q = Queue()

        p1 = Process(target=runner_proc, args=(devs[0], q))
        p2 = Process(target=runner_proc, args=(devs[1], q))
        p1.start()
        p2.start()
        PROCESS_LIST.append(p1)
        PROCESS_LIST.append(p2)
        # lte_phy_EARFCN
        outs_info = {devs[0]: [False, None], devs[1]: [False, None]}
        while True:
            
            outs_info[devs[0]][0] = False
            outs_info[devs[1]][0] = False

            e = None
            while not q.empty() or e is None:
                e = q.get()
            print("second:",time.time() - band_setting_timestamp < GLOBAL_CONFIG["SLEEP_TIME"])    
                        
            if (
                time.time() - band_setting_timestamp < GLOBAL_CONFIG["SLEEP_TIME"]
            ):
                time.sleep(0.1)
                continue

            outs_info[e[0]] = [e[1] > 0.5, e[2]]

            if outs_info[devs[0]][0] == False and outs_info[devs[1]][0] == False:
                continue

            
            print(outs_info)

            if outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == False:
                # change_band(devs[0])
                DBL_LOG.write(
                    ",".join(
                        [
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                            "1",
                            str(DEVICE_INFO[devs[0]]["band"]),
                            "0",
                            str(DEVICE_INFO[devs[1]]["band"]),
                        ]
                    )
                    + "\n"
                )
                DBL_LOG.flush()
            elif outs_info[devs[0]][0] == False and outs_info[devs[1]][0] == True:
                print('change follower band')
                change_band(devs[1])
                band_setting_timestamp = time.time()
                DBL_LOG.write(
                    ",".join(
                        [
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                            "0",
                            str(DEVICE_INFO[devs[0]]["band"]),
                            "1",
                            str(DEVICE_INFO[devs[1]]["band"]),
                        ]
                    )
                    + "\n"
                )
                DBL_LOG.flush()
            elif outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == True:
                # change_band(devs[0])
                DBL_LOG.write(
                    ",".join(
                        [
                            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f"),
                            "1",
                            str(DEVICE_INFO[devs[0]]["band"]),
                            "1",
                            str(DEVICE_INFO[devs[1]]["band"]),
                        ]
                    )
                    + "\n"
                )
                # Show prediction result during experiment. )

    except KeyboardInterrupt:
        print("Main process received KeyboardInterrupt")
        p1.join()
        p2.join()
        DBL_LOG.close()
        time.sleep(1)
        # for dev in GLOBAL_CONFIG['Device']:
        #     subprocess.Popen(
        #         " ".join(
        #             [
        #                 os.path.join(GLOBAL_CONFIG["PATH_UTILS"], "disconnect-qmi.sh"),
        #                 "-i",
        #                 dev
        #             ]
        #         ),
        #         shell=True,
        #     )
        print("Process killed, closed.")
        
