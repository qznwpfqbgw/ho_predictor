from mobile_insight.analyzer import Analyzer
from collections import deque
import time
from parser import *
from extractor import *
from utils.loop_timer import LoopTimer

class FeatureExtractor(Analyzer):
    def __init__(self, sample_interval_sec=1.0, sample_length_sec=3):
        super().__init__()
        self.add_source_callback(self.online_ue_event_filter)
        self.parsers: list[Parser] = []
        self.extractors: list[Extractor] = []
        self.sample_interval = sample_interval_sec
        self.last_sample_timestamp = None
        self.current_data = {}
        self.default_data = {}
    
        # deque is thread-safe https://docs.python.org/zh-tw/3/library/collections.html#collections.deque
        self.sample_data = deque(maxlen=int(sample_length_sec / sample_interval_sec))
        self.sample_task_thread = LoopTimer(sample_interval_sec, self.sample_task)
        
    def run(self):
        self.sample_task_thread.start()
        
    def sample_task(self):
        # print(len(self.current_data))
        # print(self.current_data)
        self.sample_data.append(self.current_data)
        # print(len(self.sample_data))
        # self.current_data = self.default_data

    def set_source(self, source):
        super().set_source(source)
        for parser in self.parsers:
            for log_type in parser.type_id:
                self.source.enable_log(log_type)

    def add_parser(self, parser: Parser):
        self.parsers.append(parser)
        if self.source is not None:
            for log_type in parser.type_id:
                self.source.enable_log(log_type)

    def add_extractor(self, extractor: Extractor):
        self.extractors.append(extractor)
        for k, v in extractor.default_output.items():
            if k not in self.current_data.keys():
                self.current_data[k] = v
                self.default_data[k] = v
            else:
                raise Exception(f"Same feature key {k}")

    def set_data_order(self, new_order):
        # print(self.current_data)
        self.current_data = {key: self.current_data[key] for key in new_order}
        self.default_data = {key: self.default_data[key] for key in new_order}
        # print(self.current_data)
        # exit(0)

    def online_ue_event_filter(self, msg):
        for parser in self.parsers:
            if msg.type_id in parser.type_id:
                parser.do_parse(msg)

        for extractor in self.extractors:
            data = extractor.do_extract()
            self.current_data.update(data)
            
        # Clear all parser storage
        for parser in self.parsers:
            parser.clear_storage()

    def get_feature_dict(self):
        return self.sample_data


if __name__ == "__main__":
    from mobile_insight.monitor import OfflineReplayer

    src = OfflineReplayer()
    src.set_input_path("./test/diag_log_sm01_2024-06-20_18-08-32.mi2log")
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

    feature_extractor = FeatureExtractor()
    feature_extractor.set_source(src)
    feature_extractor.add_parser(rrc_ota_parser)
    feature_extractor.add_parser(lte_ss_parser)
    feature_extractor.add_parser(nr_ss_parser)
    feature_extractor.add_extractor(ho_extractor)
    feature_extractor.add_extractor(mr_extractor)
    feature_extractor.add_extractor(lte_ss_extractor)
    feature_extractor.add_extractor(nr_ss_extractor)

    src.run()
