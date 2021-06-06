'''
Hides and shows script
'''
import win32gui, win32con
import logging

# Import logger
log = logging.getLogger(__name__)


# Get current foreground window
def get() -> None:
    global program
    program = win32gui.GetForegroundWindow()
    if program:
        log.info("Got foreground window")
    else:
        log.error("No foreground window found")


# Show script
def show() -> None:
    global program
    win32gui.ShowWindow(program, win32con.SW_SHOW)
    log.info("Program is now visible")


# Hide script
def hide() -> None:
    global program
    win32gui.ShowWindow(program, win32con.SW_HIDE)
    log.info("Program is now invisible")


get()
