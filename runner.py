from mobile_insight.monitor import OnlineMonitor
from actor import Actor
from predictor import *
from actor import *
from feature_extractor import FeatureExtractor
from utils.loop_timer import LoopTimer
from threading import Thread
import os
import json
from datetime import datetime as dt
from predictor import Predictor
from utils.myMsgLogger import MyMsgLogger


def get_ser(folder, dev: str):
    d2s_path = os.path.join(folder, "device_setting.json")
    with open(d2s_path, "r") as f:
        device_to_serial = json.load(f)
        if dev.startswith("sm"):
            return os.path.join(
                "/dev/serial/by-id",
                f"usb-SAMSUNG_SAMSUNG_Android_{device_to_serial[dev]}-if00-port0",
            )
        else:
            return os.path.join(
                "/dev/serial/by-id",
                f"usb-Quectel_RM500Q-GL_{device_to_serial[dev]}-if00-port0",
            )


class Runner:
    def __init__(
        self,
        feature_extractor: FeatureExtractor,
        predictor: Predictor,
        actor: Actor,
        ser: str,
        log_dir: str = None,
        baudrate=9600,
        predict_interval: float = 1.0,
    ) -> None:
        # Setup mobileinsight online monitor
        self.src = OnlineMonitor()
        self.src.set_serial_port(ser)
        self.src.set_baudrate(baudrate)

        self.feature_extractor = feature_extractor
        self.feature_extractor.set_source(self.src)
        self.predictor = predictor
        self.actor = actor

        self.pred_task = LoopTimer(predict_interval, self.predict_task)
        self.main_task = Thread(target=self.run_task, daemon=True)

        self.log_dir = self.create_log_dir(log_dir)
        self.mi2log_log_path = os.path.join(
            self.log_dir,
            "diag_log_{}_{}.mi2log".format(ser.replace('/','_'), os.path.basename(self.log_dir)),
        )
        self.xml_log_path = os.path.join(
            self.log_dir,
            "diag_log_{}_{}.xml".format(ser.replace('/','_'), os.path.basename(self.log_dir)),
        )

        dumper = MyMsgLogger()
        dumper.set_source(self.src)
        dumper.set_decoding(MyMsgLogger.XML)  # decode the message as xml
        dumper.set_dump_type(MyMsgLogger.FILE_ONLY)
        dumper.save_decoded_msg_as(self.xml_log_path)
        self.src.save_log_as(self.mi2log_log_path)

        self.dev = ser

    def create_log_dir(self, log_dir):
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

    def run(self):
        self.pred_task.start()
        self.feature_extractor.run()
        print('task running', flush=True)
        self.src.run()
        # print('task running', flush=True)

    def run_task(self):
        self.src.run()

    def predict_task(self):
        x_in = self.feature_extractor.get_feature_dict()
        pred_output = self.predictor.predict(x_in)
        self.actor.do_action(pred_output)


class DeviceRunner(Runner):
    def __init__(
        self,
        dev: str,
        verbose: float,
        feature_extractor: FeatureExtractor,
        log_dir: str = None,
        baudrate=9600,
        predict_interval: float = 1,
        predictor: Predictor = Predictor(),
        actor: Actor = Actor(),
    ) -> None:
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

        feature_extractor.add_parser(rrc_ota_parser)
        feature_extractor.add_parser(lte_ss_parser)
        feature_extractor.add_parser(nr_ss_parser)
        feature_extractor.add_extractor(ho_extractor)
        feature_extractor.add_extractor(mr_extractor)
        feature_extractor.add_extractor(lte_ss_extractor)
        feature_extractor.add_extractor(nr_ss_extractor)
        super().__init__(
            feature_extractor,
            predictor,
            actor,
            get_ser(os.path.dirname(__file__), dev),
            log_dir,
            baudrate,
            predict_interval,
        )

        verbose = min(verbose, 0.1)

        self.verbose_task = LoopTimer(predict_interval, self.predict_task)

    def show_ho(self):
        HOs = [
            "LTE_HO",
            "MN_HO",
            "SN_setup",
            "SN_Rel",
            "SN_HO",
            "Conn_Req",
            "RLF",
            "SCG_RLF",
        ]
        self.feature_extractor.get_feature_dict()
        features = {k: v for k, v in features.items() if k in HOs}

        for k, v in features.items():
            if v == 1:
                print(f"{self.dev}: HO {k} happened!!!!!")


class DefaultRunner(Runner):
    def __init__(
        self,
        ser: str,
        # verbose: float,
        feature_extractor: FeatureExtractor,
        log_dir: str = None,
        baudrate=9600,
        predict_interval: float = 1,
        predictor: Predictor = Predictor(),
        actor: Actor = Actor(),
    ) -> None:
        super().__init__(
            feature_extractor,
            predictor,
            actor,
            ser,
            log_dir,
            baudrate,
            predict_interval,
        )

        # verbose = min(verbose, 0.1)

        # self.verbose_task = LoopTimer(predict_interval, self.predict_task)

if __name__ == "__main__":
    from parser import *
    from extractor import *
    from feature_extractor import *
    from predictor.rlf_xgboost_predictor import RLF_Xgboost_Predictor
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

    feature_extractor = FeatureExtractor(sample_interval_sec=0.1, sample_length_sec = 5)
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
    
    predictor = RLF_Xgboost_Predictor()
    runner = DefaultRunner(
        ser="/tmp/ttyV1",
        predictor=predictor,
        feature_extractor=feature_extractor,
        predict_interval = 0.1
    )

    try:
        runner.run()
        while True:
            time.sleep(1)
    except Exception as e:
        import traceback

        traceback.print_exc()
