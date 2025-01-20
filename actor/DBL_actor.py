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
        if pred_output[0] > 0.5 and time.time() - self.timer_start < 0.3:
            self.counter += 1
        elif pred_output[0] > 0.5:
            self.counter = 1
            self.timer_start = time.time()
        else:
            self.counter = 0
        
        if self.counter >= 2:
            # do Action
            self.q.put((self.dev, pred_output[0], pred_output[1]))
        else:
            self.q.put((self.dev, pred_output[0], pred_output[1]))
            