from datetime import datetime as dt
import logging

log = logging.getLogger(__name__)


class PerfCheck:
    def __init__(self) -> None:
        self.previous = None
    
    def start(self):
        self.previous = dt.now()

    def check(self, task):
        if not self.previous:
            log.warning(f"Perf Check without start with task {task}")
        
        difference = dt.now() - self.previous
        log.info(f"PerfCheck ----------------> {task} needed {difference} to finish")
        self.previous = dt.now()
