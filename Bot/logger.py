import logging

# Initialize logger
FORMAT = '[%(levelname)s] - %(asctime)s: %(message)s'
logging.basicConfig(level=logging.INFO,
                    format=FORMAT,
                    filename='debug.log',
                    datefmt='%H:%M:%S')
logging.info("----------------Start-----------------")
