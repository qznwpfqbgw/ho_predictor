from .actor import Actor
import time
class DBL_Actor(Actor):
    def __init__(self, q, dev, feature_extractor):
        super().__init__()
        self.counter = 0
        self.timer_start = 0
        self.q = q
        self.dev = dev
        
    def set_feature_extractor(self, feature_extractor):
        self.feature_extractor = feature_extractor
    
    def do_action(self, pred_output):
        if pred_output == True and time.time() - self.timer_start < 0.5:
            self.counter += 1
        else:
            self.counter = 1
            self.timer_start = time.time()
        
        if self.counter >= 2:
            # do Action
            self.q.put((self.dev, True, self.feature_extractor.get_feature_dict()))
        else:
            self.q.put((self.dev, False, self.feature_extractor.get_feature_dict()))
            