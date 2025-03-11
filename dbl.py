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
import os
import random
import datetime

GLOBAL_CONFIG = None
DEVICE_INFO = None

ALL_LTE_BAND_CANDIDATE = {
    "1",
    "3",
    "7",
    "8",
    "1:3",
    "1:7",
    "1:8",
    "3:7",
    "3:8",
    "7:8",
    "1:3:7",
    "1:3:8",
    "1:7:8",
    "3:7:8",
    "1:3:7:8",
}

INIT_BAND = ["1:3:7:8", "3:8"]


def load_config(config_file):
    global GLOBAL_CONFIG
    with open(config_file, "r") as f:
        GLOBAL_CONFIG = yaml.safe_load(f)


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


def setup_modem(dev: str):
    global GLOBAL_CONFIG, DEVICE_INFO
    if dev.startswith("dummy"):
        band_candidate = ALL_LTE_BAND_CANDIDATE.copy()
        if DEVICE_INFO is not None:
            for k, v in DEVICE_INFO.items():
                band_candidate = band_candidate - {v["band"]}
        band = random.choice(list(band_candidate))
        return None, None, band

    process = subprocess.Popen(
        [os.path.join(GLOBAL_CONFIG["PATH_UTILS"], "dial-qmi.sh"), "-i", dev],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    stdout, stderr = process.communicate()

    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())

    with open(
        os.path.join(GLOBAL_CONFIG["PATH_TEMP_DIR"], f"temp-nas_{dev}"), "r"
    ) as f:
        pattern = r"\[(\/dev\/cdc-wdm\d+)\]"
        content = f.read()
        matches = re.findall(pattern, content)[0]
        wdm = matches
        pattern = r"CID:\s*'(\d+)'"
        matches = re.findall(pattern, content)[0]
        cid = matches

    band_candidate = ALL_LTE_BAND_CANDIDATE.copy()
    if DEVICE_INFO is not None:
        for k, v in DEVICE_INFO.items():
            band_candidate = band_candidate - {v["band"]}
    band = random.choice(list(band_candidate))

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
    stdout, stderr = process.communicate()

    if stdout:
        print(stdout.decode())
    if stderr:
        print(stderr.decode())

    return wdm, cid, band


def change_band(dev):
    global GLOBAL_CONFIG, DEVICE_INFO

    band_candidate = ALL_LTE_BAND_CANDIDATE.copy()
    for k, v in DEVICE_INFO.items():
        band_candidate = band_candidate - {v["band"]}

    band = random.choice(list(band_candidate))

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


if __name__ == "__main__":
    # parser = argparse.ArgumentParser()
    # parser.add_argument('-c', '--config_file',
    #                     default='config.yml', help="Config file (yaml)")
    # args = parser.parse_args()

    # # load_config(args.config_file)
    load_config("config.yml")
    log_dir = create_log_dir()
    GLOBAL_CONFIG["LOG_DIR"] = log_dir

    devs = GLOBAL_CONFIG["Device"]

    if len(devs) != 2:
        raise Exception("DBL need at least 2 device")

    # Setup modem
    DEVICE_INFO = {}
    for dev in devs:
        wdm, cid, band = setup_modem(dev)
        DEVICE_INFO[dev] = {"wdm": wdm, "cid": cid, "band": band}
    band_setting_timestamp = time.time() - 10

    f = os.path.join(GLOBAL_CONFIG["LOG_DIR"], "cmd_record.csv")
    dbl_log = open(f, "w")
    print("Timestamp,dev_0,band_0,dev_1,band_1", file=dbl_log, flush=True)
    dbl_log.write(
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

        # lte_phy_EARFCN
        outs_info = {devs[0]: [False, None], devs[1]: [False, None]}
        while True:
            
            outs_info[devs[0]][0] = False
            outs_info[devs[1]][0] = False

            e = None
            while not q.empty() or e is None:
                e = q.get()
                print("first", not q.empty() or e is None)
            print("second:",time.time() - band_setting_timestamp < GLOBAL_CONFIG["SLEEP_TIME"])    
                        
            if (
                time.time() - band_setting_timestamp < GLOBAL_CONFIG["SLEEP_TIME"]
            ):
                time.sleep(0.1)
                continue

            outs_info[e[0]] = [e[1] > 0.5, e[2]]
            
            print("third:",outs_info[devs[0]][0] == False and outs_info[devs[0]][0] == False)
            print("third1:",outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == False)
            print("third2:",outs_info[devs[0]][0] == False and outs_info[devs[1]][0] == True)

            if outs_info[devs[0]][0] == False and outs_info[devs[1]][0] == False:
                continue

            
            print(outs_info)

            if outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == False:
                # change_band(devs[0])
                dbl_log.write(
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
            elif outs_info[devs[0]][0] == False and outs_info[devs[1]][0] == True:
                print('change follower band')
                change_follower_band(devs[1])
                band_setting_timestamp = time.time()
                dbl_log.write(
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
            elif outs_info[devs[0]][0] == True and outs_info[devs[1]][0] == True:
                # change_band(devs[0])
                dbl_log.write(
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
        dbl_log.close()
        time.sleep(1)
        for dev in GLOBAL_CONFIG['Device']:
            subprocess.Popen(
                " ".join(
                    [
                        os.path.join(GLOBAL_CONFIG["PATH_UTILS"], "disconnect-qmi.sh"),
                        "-i",
                        dev
                    ]
                ),
                shell=True,
            )
        print("Process killed, closed.")
        
