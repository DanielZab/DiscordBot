import os, shutil, logging

log = logging.getLogger(__name__)


def delete_directory(direc):
    if os.path.exists(direc) and os.path.isdir(direc):
        shutil.rmtree(direc)


def reset_directories():

    delete_directory('temp')
    os.mkdir('temp')

    log.info("Temp was reset")


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

def get_playlists():

    log.info("Getting playlist directories")

    playlists = []
    if os.path.exists("playlists"):
        folders = os.listdir("playlists")
        for folder in folders:
            if os.path.isdir("playlists\\" + folder):
                playlists.append(folder)
    
    return playlists
