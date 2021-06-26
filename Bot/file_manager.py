import os, shutil, logging

log = logging.getLogger(__name__)

def reset_directories():
    if os.path.exists('queue') and os.path.isdir('queue'):

        shutil.rmtree('queue')

    os.mkdir('queue')

    log.info("Queue was reset")

    if os.path.exists('test') and os.path.isdir('test'):

        shutil.rmtree('test')

    os.mkdir('test')

    log.info("Test was reset")