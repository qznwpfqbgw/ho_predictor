import re
import subprocess
import argparse

EUTRA_BANDS = {
    1: (2110, 1920, 0),
    2: (1930, 1850, 600),
    3: (1805, 1710, 1200),
    4: (2110, 1710, 1950),
    5: (869, 824, 2400),
    7: (2620, 2500, 2750),
    8: (925, 880, 3450),
    20: (791, 832, 6150),
    28: (758, 703, 9210),
    38: (2570, 2570, 37750),
    40: (2300, 2300, 38650),
}


def eutra_arfcn_to_band(arfcn):
    for band, (f_dl_low, f_ul_low, n_offs) in EUTRA_BANDS.items():
        if n_offs <= arfcn < n_offs + 600:
            return band
    return None


def eutra_arfcn_to_freq(arfcn, direction="downlink"):
    for band, (f_dl_low, f_ul_low, n_offs) in EUTRA_BANDS.items():
        if n_offs <= arfcn < n_offs + 600:
            freq_mhz = (arfcn - n_offs) * 0.1 + (
                f_dl_low if direction == "downlink" else f_ul_low
            )
            return freq_mhz
    return None


def freq_to_eutra_arfcn(freq_mhz, direction="downlink"):
    for band, (f_dl_low, f_ul_low, n_offs) in EUTRA_BANDS.items():
        f_low = f_dl_low if direction == "downlink" else f_ul_low
        if f_low <= freq_mhz < f_low + 60:
            return int((freq_mhz - f_low) / 0.1 + n_offs)
    return None


def parse_lte_info(data):
    result = []

    # 匹配 EUTRA 的頻段資訊
    freq_matches = re.finditer(r"EUTRA Absolute RF Channel Number: '(\d+)'", data)
    for freq_match in freq_matches:
        arfcn = int(freq_match.group(1))

        # 匹配每個cell的資訊
        cells = re.finditer(
            r"Cell \[\d+\]:\s+Physical Cell ID: '(\d+)'\s+RSRQ: '(-?\d+\.\d+)' dB\s+RSRP: '(-?\d+\.\d+)' dBm\s+RSSI: '(-?\d+\.\d+)' dBm",
            data,
        )
        for cell in cells:
            result.append(
                {
                    "cell_id": int(cell.group(1)),
                    "rsrq": float(cell.group(2)),
                    "rsrp": float(cell.group(3)),
                    "rssi": float(cell.group(4)),
                    # "eutra_arfcn": arfcn,  # 加入 EUTRA ARFCN,
                    "band": eutra_arfcn_to_band(arfcn),
                }
            )

    return result


def parse_info(data):
    result = []
    intra_lte = data[
        data.find("Intrafrequency")
        + len("Intrafrequency LTE Info") : data.find("Interfrequency LTE Info")
    ]
    result += parse_lte_info(intra_lte)
    inter_lte = data[
        data.find("Interfrequency")
        + len("Interfrequency LTE Info") : data.find("LTE Info Neighboring GSM")
    ]
    result += parse_lte_info(inter_lte)
    return result


# 測試用字串
lte_string = """
[/dev/cdc-wdm1] Successfully got cell location info
Intrafrequency LTE Info
        UE In Idle: 'no'
        PLMN: '46692'
        Tracking Area Code: '11200'
        Global Cell ID: '54613013'
        EUTRA Absolute RF Channel Number: '3650' (E-UTRA band 8: 900)
        Serving Cell ID: '13'
        Cell [0]:
                Physical Cell ID: '13'
                RSRQ: '-9.9' dB
                RSRP: '-88.2' dBm
                RSSI: '-60.0' dBm
        Cell [1]:
                Physical Cell ID: '21'
                RSRQ: '-15.6' dB
                RSRP: '-95.9' dBm
                RSSI: '-71.8' dBm
Interfrequency LTE Info
        UE In Idle: 'no'
        Frequency [0]:
                EUTRA Absolute RF Channel Number: '3050' (E-UTRA band 7: 2600)
                Selection RX Level Low Threshold: '0'
                Cell Selection RX Level High Threshold: '0'
                Cell [0]:
                        Physical Cell ID: '13'
                        RSRQ: '-16.3' dB
                        RSRP: '-117.7' dBm
                        RSSI: '-92.3' dBm
                        Cell Selection RX Level: '0'
                Cell [1]:
                        Physical Cell ID: '21'
                        RSRQ: '-18.0' dB
                        RSRP: '-118.9' dBm
                        RSSI: '-92.3' dBm
                        Cell Selection RX Level: '0'
                Cell [2]:
                        Physical Cell ID: '5'
                        RSRQ: '-19.7' dB
                        RSRP: '-120.1' dBm
                        RSSI: '-92.3' dBm
                        Cell Selection RX Level: '0'
        Frequency [1]:
                EUTRA Absolute RF Channel Number: '1750' (E-UTRA band 3: 1800+)
                Selection RX Level Low Threshold: '0'
                Cell Selection RX Level High Threshold: '0'
                Cell [0]:
                        Physical Cell ID: '13'
                        RSRQ: '-16.3' dB
                        RSRP: '-116.4' dBm
                        RSSI: '-92.0' dBm
                        Cell Selection RX Level: '0'
                Cell [1]:
                        Physical Cell ID: '21'
                        RSRQ: '-18.8' dB
                        RSRP: '-119.3' dBm
                        RSSI: '-92.0' dBm
                        Cell Selection RX Level: '0'
                Cell [2]:
                        Physical Cell ID: '5'
                        RSRQ: '-20.0' dB
                        RSRP: '-123.2' dBm
                        RSSI: '-92.0' dBm
                        Cell Selection RX Level: '0'
LTE Info Neighboring GSM
        UE In Idle: 'no'
LTE Info Neighboring WCDMA
        UE In Idle: 'no'
LTE Timing Advance: '0' us
[/dev/cdc-wdm1] Client ID not released:
        Service: 'nas'
            CID: '4'
"""


def get_cell_info(wdm, nas_cid):
    with subprocess.Popen(
        [
            "sudo",
            "qmicli",
            "-d",
            wdm,
            "--nas-get-cell-location-info",
            "--client-cid",
            nas_cid,
            "--client-no-release-cid",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        stdout, stderr = proc.communicate()

    return parse_info(stdout)
    


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--wdm", type=str)
    parser.add_argument("-c", "--nas_cid", type=str)
    args = parser.parse_args()

    with subprocess.Popen(
        [
            "sudo",
            "qmicli",
            "-d",
            args.wdm,
            "--nas-get-cell-location-info",
            "--client-cid",
            args.nas_cid,
            "--client-no-release-cid",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        stdout, stderr = proc.communicate()

    print(parse_info(stdout))
