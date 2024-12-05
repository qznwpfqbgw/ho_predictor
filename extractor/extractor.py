import warnings

warnings.filterwarnings("ignore")


class Extractor:
    def __init__(self) -> None:
        self.source_parser = None
        self.default_output = {}

    def set_source_parser(self, parser):
        self.source_parser = parser

    def extract(self, df) -> dict:
        pass

    def do_extract(self):
        df = self.source_parser.get_storage_df()
        if len(df) == 0:
            return {}
        out_dict = self.extract(df)

        return out_dict

    def get_feature_key(self):
        return self.default_output.keys()
