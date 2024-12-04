from .extractor import Extractor
import pandas as pd
import numpy as np


class NR_Signal_Strength_Extractor(Extractor):
    def __init__(self) -> None:
        super().__init__()
        self.default_output = {
            "nr_best_rsrq": -200,
            "nr_best_rsrp": -200,
            "current_nr_rsrq": -200,
            "current_nr_rsrp": -200,
        }

    def extract(self, df) -> dict:
        nr_phy_rsrq_cols = [f"RSRQ{i}" for i in range(12)]
        nr_phy_rsrp_cols = [f"RSRP{i}" for i in range(12)]
        if len(df) == 0:
            return self.default_output
        df[nr_phy_rsrq_cols + nr_phy_rsrp_cols] = df[
            nr_phy_rsrq_cols + nr_phy_rsrp_cols
        ].fillna(-200, inplace=True)

        # Best RSRQ and RSRP values for NR and LTE (find maximum per row)
        nr_best_rsrq = df[nr_phy_rsrq_cols].max(axis=1)
        nr_best_rsrp = df[nr_phy_rsrp_cols].max(axis=1)

        # Handling the current PHY based on the Serving Cell Index
        current_nr_mask = (~df["Serving Cell Index"].isna()) & (
            df["Serving Cell Index"] != 255
        )

        df.loc[current_nr_mask, "current_nr_RSRQ"] = df.apply(
            lambda row: (
                row[f"RSRQ{int(row['Serving Cell Index'])}"]
                if pd.notna(row["Serving Cell Index"])
                and int(row["Serving Cell Index"]) != 255
                else -200
            ),
            axis=1,
        )
        df.loc[current_nr_mask, "current_nr_RSRP"] = df.apply(
            lambda row: (
                row[f"RSRP{int(row['Serving Cell Index'])}"]
                if pd.notna(row["Serving Cell Index"])
                and int(row["Serving Cell Index"]) != 255
                else -200
            ),
            axis=1,
        )
        
        df.replace(-200, np.nan, inplace=True)
        df.fillna(method='ffill', inplace=True)
        nr_best_rsrq.replace(-200, np.nan, inplace=True)
        nr_best_rsrq.fillna(method='ffill', inplace=True)
        nr_best_rsrp.replace(-200, np.nan, inplace=True)
        nr_best_rsrp.fillna(method='ffill', inplace=True)

        result_dict = {
            "nr_best_rsrq": float(nr_best_rsrq.tail(1).values[0]) if not pd.isna(nr_best_rsrq.tail(1).values[0]) else -200,
            "nr_best_rsrp": float(nr_best_rsrp.tail(1).values[0]) if not pd.isna(nr_best_rsrp.tail(1).values[0]) else -200,
            "current_nr_rsrq": float(df["current_nr_RSRQ"].tail(1).values[0]) if not pd.isna(df["current_nr_RSRQ"].tail(1).values[0]) else -200,
            "current_nr_rsrp": float(df["current_nr_RSRP"].tail(1).values[0]) if not pd.isna(df["current_nr_RSRP"].tail(1).values[0]) else -200,
        }

        return result_dict
