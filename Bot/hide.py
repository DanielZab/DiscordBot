'''
Hides and shows the current python console
'''
import win32gui, win32con
import logging

log = logging.getLogger(__name__)


class ConsoleVisibility:
    '''
    Controls the visibility of the python console.
    '''

    def __init__(self) -> None:
        self.program = self.get()

    def get(self) -> None:
        '''
        Gets the current window in the foreground in order to change its
        visibility later. The target is the python console, therefore it's important
        to call this function as fast as possible after the launch of main.py.
        '''

        program = win32gui.GetForegroundWindow()

        if program:
            log.info("Got foreground window")
        else:
            log.error("No foreground window found")
        
        return program

    # Show script
    def show(self) -> None:
        '''
        Change the visibility of python console to visible
        '''

        win32gui.ShowWindow(self.program, win32con.SW_SHOW)
        log.info(f"Process {self.program} is now visible")

    def hide(self) -> None:
        '''
        Change the visibility of python console to invisible
        '''

        win32gui.ShowWindow(self.program, win32con.SW_HIDE)
        log.info(f"Process {self.program} is now invisible")


console = ConsoleVisibility()
