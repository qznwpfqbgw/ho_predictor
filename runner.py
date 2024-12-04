from mobile_insight.monitor import OnlineMonitor
from predictor import *
from actor import *
from feature_extractor import FeatureExtractor
from threading import Timer, Thread, Event
import os
import json
from datetime import datetime as dt
from utils.myMsgLogger import MyMsgLogger

def get_ser(folder, dev):
    d2s_path = os.path.join(folder, "device_setting.json")
    with open(d2s_path, "r") as f:
        device_to_serial = json.load(f)
        return os.path.join(
            "/dev/serial/by-id",
            f"usb-SAMSUNG_SAMSUNG_Android_{device_to_serial[dev]}-if00-port0",
        )


class LoopTimer(Thread):
    def __init__(self, interval, function, *args, **kwargs):
        Thread.__init__(self)
        self.daemon = True
        self.stopped = Event()
        self.interval = interval
        self.function = function
        self.args = args if args is not None else []
        self.kwargs = kwargs if kwargs is not None else {}

    def stop(self):
        self.stopped.set()
        self.join()

    def run(self):
        while not self.stopped.wait(self.interval):
            if not self.stopped.is_set():
                self.function(*self.args, **self.kwargs)
            else:
                break


class Runner:
    def __init__(
        self,
        feature_extractor: FeatureExtractor,
        predictor: Predictor,
        actor: Actor,
        dev: str,
        log_dir: str = None,
        baudrate=9600,
        predict_interval: float = 1.0,
    ) -> None:
        # Setup mobileinsight online monitor
        self.src = OnlineMonitor()
        self.src.set_serial_port(get_ser(os.path.dirname(__file__), dev))
        self.src.set_baudrate(baudrate)
        
        self.feature_extractor = feature_extractor
        self.feature_extractor.set_source(self.src)
        self.predictor = predictor
        self.actor = actor

        self.pred_task = LoopTimer(predict_interval, self.predict_task)
        self.main_task = Thread(target=self.run_task, daemon=True)
        
        self.log_dir = self.create_log_dir()
        self.mi2log_log_path = os.path.join(self.log_dir, "diag_log_{}_{}.mi2log".format(dev, os.path.basename(self.log_dir)))
        self.xml_log_path = os.path.join(self.log_dir, "diag_log_{}_{}.xml".format(dev, os.path.basename(self.log_dir)))
        
        dumper = MyMsgLogger()
        dumper.set_source(self.src)
        dumper.set_decoding(MyMsgLogger.XML)  # decode the message as xml
        dumper.set_dump_type(MyMsgLogger.ALL)
        dumper.save_decoded_msg_as(self.xml_log_path)
        self.src.save_log_as(self.mi2log_log_path)
    
    def create_log_dir(self, log_dir):
        if log_dir is None:
            now = dt.today()
            n = [str(x) for x in [now.year, now.month, now.day, now.hour, now.minute, now.second]]
            n = [x.zfill(2) for x in n] 
            n = '-'.join(n[:3]) + '_' + '-'.join(n[3:])
            os.umask(0)
            log_dir = os.path.join(os.path.dirname(__file__), 'log', str(n))
        os.makedirs(log_dir, exist_ok=True)
        return log_dir


    def run(self):
        self.main_task.start()
        self.pred_task.start()
        # print('task running', flush=True)

    def run_task(self):
        self.src.run()

    def predict_task(self):
        x_in = self.feature_extractor.get_feature_dict()
        # print("predict", flush=True)
        pred_output = self.predictor.predict(x_in)
        self.actor.do_action(pred_output)


if __name__ == "__main__":
    from parser import *
    from extractor import *
    from feature_extractor import *

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

    feature_extractor = FeatureExtractor(offline=True)
    feature_extractor.add_parser(rrc_ota_parser)
    feature_extractor.add_parser(lte_ss_parser)
    feature_extractor.add_parser(nr_ss_parser)
    feature_extractor.add_extractor(ho_extractor)
    feature_extractor.add_extractor(mr_extractor)
    feature_extractor.add_extractor(lte_ss_extractor)
    feature_extractor.add_extractor(nr_ss_extractor)

    runner = Runner(
        feature_extractor=feature_extractor,
        predictor=Predictor(),
        actor=Actor(),
        dev="sm01",
    )
    
    try:
    
        runner.run()
        while True:
            time.sleep(1)
    except Exception as e:
        import traceback
        traceback.print_exc()
        
