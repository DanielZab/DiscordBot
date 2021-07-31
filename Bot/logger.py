import logging
import os

# Delete previous debug log
if os.path.exists("debug.log"):
    os.remove("debug.log")

# Initialize logger
FORMAT = '[%(levelname)s] - %(asctime)s: %(message)s'
logging.basicConfig(handlers=[logging.FileHandler(filename='debug.log', encoding='utf-8', mode='a+')],
                    level=logging.INFO,
                    format=FORMAT,
                    datefmt='%H:%M:%S')
logging.info("----------------Start-----------------")