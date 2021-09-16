'''
Manages directories and files
'''
import os, shutil, logging

log = logging.getLogger(__name__)


def delete_directory(direc: str) -> None:
    '''
    Deletes a directory
    '''

    # Check if giver path exists and is a directory
    if os.path.exists(direc) and os.path.isdir(direc):

        # Remove direcory and all files in it
        shutil.rmtree(direc)


def reset_directories() -> None:
    '''
    Deletes all contents in queue, temp and captions directories
    '''

    # Reset queue directory
    delete_directory('queue')
    os.mkdir('queue')

    # Reset queue directory
    delete_directory('temp')
    os.mkdir('temp')

    # Reset queue directory
    delete_directory('captions')
    os.mkdir('captions')

    log.info("Directory reset complete")


def create_playlist_directory(name: str) -> str:
    '''
    Adapts the playlist's name, creates a directory for it and returns its new name
    Raises ValueError if playlist name is reserved
    Raises FileExistsError if name is already occupied
    '''

    log.debug("Creating playlist " + str(name))

    # Create playlists folder if it doesn't exist
    if not (os.path.exists("playlists") and os.path.isdir("playlists")):
        os.mkdir("playlists")

    if name:

        # Remove invalid characters
        forbidden_chars = '<>:"/\\|?*\''
        for char in forbidden_chars:
            name = name.replace(char, "")

        # Detect invalid names
        forbidden_names = ["playlists", "playlist"]
        if any(name.lower() == e.lower() for e in forbidden_names):
            log.warning("Forbidden name for playlist")
            raise ValueError

        # Check if playlist name isn't empty after removal of forbidden chars
        if len(name) > 0:

            # Try to create directory
            try:
                os.mkdir("playlists\\" + name)
                log.info("Created playlist directory: playlists\\" + str(name))
                return name

            except FileExistsError:
                log.error(f"Couldn't create playlist {name}, it already exists")
                raise FileExistsError

    # Error detection
    log.error("Invalid playlist name")
    raise ValueError


def get_playlists():
    '''
    Get all playlists in 'playlists' folder
    '''

    log.info("Getting playlist directories")

    # Create container for the playlists
    playlists = []

    # Check if playlists directory exists
    if os.path.exists("playlists"):

        # Loop thorugh all files in playlists
        folders = os.listdir("playlists")
        for folder in folders:

            # Check if file is a directory
            if os.path.isdir("playlists\\" + folder):

                # Add playlist to container
                playlists.append(folder)

    return playlists
