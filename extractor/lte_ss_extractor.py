from .extractor import Extractor
import pandas as pd
import numpy as np

class Lte_Signal_Strength_Extractor(Extractor):
    def __init__(self) -> None:
        super().__init__()
        self.default_output = {
            "lte_best_rsrq": -200,
            "lte_best_rsrp": -200,
            "current_lte_rsrq": -200,
            "current_lte_rsrp": -200,
            "scell1_lte_rsrq": -200,
            "scell1_lte_rsrp": -200,
            "scell2_lte_rsrq": -200,
            "scell2_lte_rsrp": -200,
            "scell3_lte_rsrq": -200,
            "scell3_lte_rsrp": -200,
            "lte_phy_EARFCN": 0,
            "lte_phy_Number_of_Neighbor_Cells": 0
        }
        
    def extract(self, df) -> dict:
        lte_phy_rsrq_cols = [f"RSRQ{i}" for i in range(1, 12)]
        lte_phy_rsrp_cols = [f"RSRP{i}" for i in range(1, 12)]
        if len(df) == 0:
            return self.default_output
        
        df[lte_phy_rsrq_cols + lte_phy_rsrp_cols] = df[lte_phy_rsrq_cols + lte_phy_rsrp_cols].fillna(-200)

        # Best RSRQ and RSRP values for NR and LTE (find maximum per row)
        lte_best_rsrq = df[lte_phy_rsrq_cols].max(axis=1)
        lte_best_rsrp = df[lte_phy_rsrp_cols].max(axis=1)

        df.loc[
            df["Serving Cell Index"] == "PCell",
            ["current_lte_RSRQ", "current_lte_RSRP"],
        ] = df[["RSRQ(dB)", "RSRP(dBm)"]].values[
            df["Serving Cell Index"] == "PCell"
        ]
        df.loc[
            df["Serving Cell Index"] == "1_SCell",
            ["scell1_RSRQ", "scell1_RSRP"],
        ] = df[["RSRQ(dB)", "RSRP(dBm)"]].values[
            df["Serving Cell Index"] == "1_SCell"
        ]
        df.loc[
            df["Serving Cell Index"] == "2_SCell",
            ["scell2_RSRQ", "scell2_RSRP"],
        ] = df[["RSRQ(dB)", "RSRP(dBm)"]].values[
            df["Serving Cell Index"] == "2_SCell"
        ]
        df.loc[
            df["Serving Cell Index"] == "(MI)Unknown",
            ["scell3_RSRQ", "scell3_RSRP"],
        ] = df[["RSRQ(dB)", "RSRP(dBm)"]].values[
            df["Serving Cell Index"] == "(MI)Unknown"
        ]
        
        df.replace(-200, np.nan, inplace=True)
        df.fillna(method='ffill', inplace=True)
        lte_best_rsrq.replace(-200, np.nan, inplace=True)
        lte_best_rsrq.fillna(method='ffill', inplace=True)
        lte_best_rsrp.replace(-200, np.nan, inplace=True)
        lte_best_rsrp.fillna(method='ffill', inplace=True)
        

        result_dict = {
            "lte_best_rsrq": float(lte_best_rsrq.tail(1).values[0]) if not pd.isna(lte_best_rsrq.tail(1).values[0]) else -200, 
            "lte_best_rsrp": float(lte_best_rsrp.tail(1).values[0]) if not pd.isna(lte_best_rsrp.tail(1).values[0]) else -200,
            "current_lte_rsrq": float(df["current_lte_RSRQ"].tail(1).values[0]) if not pd.isna(df["current_lte_RSRQ"].tail(1).values[0]) else -200,
            "current_lte_rsrp": float(df["current_lte_RSRP"].tail(1).values[0]) if not pd.isna(df["current_lte_RSRP"].tail(1).values[0]) else -200,
            "scell1_lte_rsrq": float(df["scell1_RSRQ"].tail(1).values[0]) if not pd.isna(df["scell1_RSRQ"].tail(1).values[0]) else -200,
            "scell1_lte_rsrp": float(df["scell1_RSRP"].tail(1).values[0]) if not pd.isna(df["scell1_RSRP"].tail(1).values[0]) else -200,
            "scell2_lte_rsrq": float(df["scell2_RSRQ"].tail(1).values[0]) if not pd.isna(df["scell2_RSRQ"].tail(1).values[0]) else -200,
            "scell2_lte_rsrp": float(df["scell2_RSRP"].tail(1).values[0]) if not pd.isna(df["scell2_RSRP"].tail(1).values[0]) else -200,
            "scell3_lte_rsrq": float(df["scell3_RSRQ"].tail(1).values[0]) if not pd.isna(df["scell3_RSRQ"].tail(1).values[0]) else -200,
            "scell3_lte_rsrp": float(df["scell3_RSRP"].tail(1).values[0]) if not pd.isna(df["scell3_RSRP"].tail(1).values[0]) else -200,
            "lte_phy_EARFCN": int(df['EARFCN'].tail(1).values[0]) if not pd.isna(df['EARFCN'].tail(1).values[0]) else 0,
            "lte_phy_Number_of_Neighbor_Cells": int(df['Number of Neighbor Cells'].tail(1).values[0]) if not pd.isna(df['Number of Neighbor Cells'].tail(1).values[0]) else 0,
        }
        
        return result_dict