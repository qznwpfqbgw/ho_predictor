from .predictor import Predictor
import xgboost as xgb
import numpy as np
import time
class RLF_Xgboost_Predictor(Predictor):
    def __init__(self, model_path):
        super().__init__()
        self.model = xgb.Booster()
        self.model.load_model(
            model_path
        )
        print('loading model',flush=True)

    def predict(self, x_in):
        all_keys = [
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

        if len(x_in) == x_in.maxlen and x_in[-1]['lte_phy_EARFCN'] != 0:
            x_in_np = np.array([
                [d.get(key, np.nan) for key in all_keys]
                for d in x_in
            ]).flatten().reshape(1,-1)
            x = xgb.DMatrix(x_in_np)
            y = self.model.predict(x)
            if y > 0.5:
                print(time.time(), ": Close to RLF !!!")
            return y[0], x_in[-1]['lte_phy_EARFCN']
        return 0, 0
