import time

class Timer:
    def __init__(self):
        self.start_time = None
        self.end_time = None

    def start(self):
        self.start_time = time.perf_counter()
        return self
    
    def stop(self):
        self.end_time = time.perf_counter()
        return self
    
    def elapsed(self):
        value = -1
        if self.start_time is None:
            raise ValueError("Timer has not been set. Call start() to start the timer.")
        if self.end_time is None:
            value = time.perf_counter() - self.start_time
        else:
            value = self.end_time - self.start_time
        return self.format_elapsed(value)
    
    def reset(self):
        self.start_time = None
        self.end_time = None
        return self
    
    def format_elapsed(self, seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = seconds % 60
        
        if hours > 0:
            return f"{hours}h {minutes}m {secs:.1f}s"
        elif minutes > 0:
            return f"{minutes}m {secs:.1f}s"
        else:
            return f"{secs:.2f}s"
