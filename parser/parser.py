import pandas as pd
class Parser:
    def __init__(self) -> None:
        self.type_id = []
        self.storage_df = pd.DataFrame()
    
    def parse(self, msg):
        pass
    
    def do_parse(self, msg):
        self.storage_df = pd.concat([self.storage_df, pd.DataFrame(self.parse(msg))], ignore_index=True)
        
    def get_storage_df(self):
        return self.storage_df
    
    def clear_storage(self):
        self.storage_df = self.storage_df.iloc[0:0]