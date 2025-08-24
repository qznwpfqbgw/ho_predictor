bit_map = {
    "b1": 1,
    "b3": 2,
    "b7": 4,
    "b8": 8
}

def band_str_to_int(band_str, sep='_'):
    bands = band_str.split(sep)
    res = 0
    for band in bands:
        res += bit_map[band]
    return res

def band_int_to_str(band_int, sep = "_"):
    bands = []
    for band, value in bit_map.items():
        if band_int & value:
            bands.append(band)
    
    return sep.join(bands)

if __name__ == "__main__":
    bandstr = "b1_b3_b8_b7"
    print(band_str_to_int(bandstr))
    print(band_int_to_str(band_str_to_int(bandstr)))
    print(band_int_to_str(204))