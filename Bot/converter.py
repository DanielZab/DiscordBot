'''
Collection of all format and type conversions
'''
import logging
import re

log = logging.getLogger(__name__)


def convert_url(url: str, id_only: bool = False, playlist: bool = False) -> str:
    '''
    Converts youtube urls to a unique format
    id_only specifies, whether to return only the id, or the whole url
    playlist specifies, whether the url refers to a playlist or a video
    Raises a ValueError when url is invalid
    '''

    log.info("Converting url")

    # Match id
    if playlist:
        match = re.match(r"^https?://(www\.)?youtube\.[a-zA-Z0-9]{2,4}.*l(ist)?=(?P<id>[^#&?%\s]+).*$", url)
    else:
        match = re.match(r"^https?://(?:www\.|m\.)?youtu(?:.*\.[A-Za-z0-9]{2,4}.*(?:/user/\w+#p(?:/a)?/u/\d+/|/e(?:mbed)?/|/vi?/|(watch\?)?vi?(?:=|%))|\.be/)(3D)?(?P<id>[^#&?%\s]+).*$", url)

    # Check if id was found
    if match:

        # Return the correct string
        if id_only:
            result = match.group('id')

        elif playlist:
            result = f"https://www.youtube.com/playlist?list={match.group('id')}"

        else:
            result = f"https://www.youtube.com/watch?v={match.group('id')}"

        log.info(f"Converted to {result}")
        return result

    # Otherwise raise ValueError
    else:
        log.error("Invalid url")
        raise ValueError


def convert_time(s: int) -> tuple:
    '''
    Converts time from seconds to a tuple containing hours, minutes and seconds
    '''

    hours, s = divmod(s, 3600)
    mins, sec = divmod(s, 60)

    return int(hours), int(mins), int(sec)


def format_time_ffmpeg(s: int) -> str:
    '''
    Converts seconds to a ffmpeg time format
    '''

    t = convert_time(s)

    return "{:02d}:{:02d}:{:02d}".format(t[0], t[1], t[2])


def get_name_from_path(path: str) -> str:
    '''
    Gets the name of a song from its path
    '''

    # Match path
    match = re.match(r"^[^\\]*\\(\\)?([a-zA-Z0-9]+\\(\\)?)?(?P<name>.*)\.[a-zA-Z0-9]{2,4}$", path)

    # Return path if found
    if match:
        name = match.group("name")
        log.info(f"Got name: {name}")
        return name

    else:
        log.warning("Couldn't get name from path {path}")
        return None
