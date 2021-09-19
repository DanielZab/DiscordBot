'''
Contains the PerfCheck class
'''
from datetime import datetime as dt
import logging

log = logging.getLogger(__name__)


class PerfCheck:
    '''
    Exists for debugging purposes only and measures how
    long certain code snippets need for their completion
    '''
    def __init__(self) -> None:
        self.previous = None
    
    def start(self):
        '''
        Stores current datetime, marks the start of the measurement
        '''

        self.previous = dt.now()

    def check(self, task):
        '''
        Calculates the time difference between the last and this call and
        prints the result in the logs
        '''

        # Check if measurement was started previously
        if not self.previous:
            log.warning(f"Perf Check called without starting. Task: {task}")
            return
        
        # Calculate and print the time difference
        difference = dt.now() - self.previous
        log.info(f"PerfCheck ----------------> {task} needed {difference} to finish")

        # Store the current datetime
        self.previous = dt.now()
