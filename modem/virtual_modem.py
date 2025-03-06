class virtual_modem:
    def __init__(self, dev, band_candidate_serial_pair, init_bands):
        self.dev = dev
        """
        Example of band_candidate_serial_pair format
        band_candidate_serial_pair = {
            "b3": "/tmp/ttyV0",
        }
        """
        self.band_candidate_serial_pair = band_candidate_serial_pair
        
    def change_band(self, dev, GLOBAL_CONFIG, DEVICE_INFO):
        pass
    
    def setup_modem(self, dev, GLOBAL_CONFIG, DEVICE_INFO):
        pass
    
    def 