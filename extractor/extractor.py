import warnings
warnings.filterwarnings("ignore")

class Extractor:
    def __init__(self) -> None:
        self.source_parser = None
        self.default_output = {}
        self.extract_callbacks = []

    def set_source_parser(self, parser):
        self.source_parser = parser

    def extract(self, df) -> dict:
        pass

    def do_extract(self):
        df = self.source_parser.get_storage_df()
        out_dict = self.extract(df)
        
        for callback in self.extract_callbacks:
            callback(out_dict)
        
        return out_dict
    
    def get_feature_key(self):
        return self.default_output.keys()
