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

def create_playlist_directory(name: str):

    log.info("Creating playlist " + str(name))

    if not (os.path.exists("playlists") and os.path.isdir("playlists")):
        os.mkdir("playlists")

    if name:
        # Remove invalid characters
        forbidden_chars = '<>:"/\\|?*`'
        for char in forbidden_chars:
            name = name.replace(char, "")

        if len(name) > 0:
        # Create directory
            try:
                os.mkdir("playlists\\" + name)
                return name

            except Exception as e:

                log.error(f"Couldn't create playlist, name: {name}, exception: " + str(e))

                raise ValueError
        else:
            log.error("Invalid playlist name")
            raise ValueError
    else:
        log.error("Invalid playlist name")
        raise ValueError