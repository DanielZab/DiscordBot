import logging
import re
log = logging.getLogger(__name__)

def convert_url(url: str, id_only: bool = False, playlist: bool = False) -> str:
    '''
    Convert youtube url to a uniform format
    '''

    log.info("Converting url")

    # Match id
    if playlist:
        match = re.match(r"^https?://(www\.)?youtube\.[a-zA-Z0-9]{2,4}.*l(ist)?=(?P<id>[^#&?%\s]+).*$", url)
    else:
        match = re.match(r"^https?://(?:www\.|m\.)?youtu(?:.*\.[A-Za-z0-9]{2,4}.*(?:/user/\w+#p(?:/a)?/u/\d+/|/e(?:mbed)?/|/vi?/|(watch\?)?vi?(?:=|%))|\.be/)(3D)?(?P<id>[^#&?%\s]+).*$", url)

    if match:

        if id_only:
            return match.group('id')
        result = f"https://www.youtube.com/watch?v={match.group('id')}"
        log.info(f"Converted to: {result}")
        return result

    else:
        log.error("Invalid url")
        raise ValueError


def convert_time(s: int) -> tuple:
    '''
    Converts time from seconds to hours, minutes and seconds
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


def get_name_from_path(path) -> str:
    '''
    Gets the name of a song from its path
    '''

    match = re.match(r"^[^\\]*\\(\\)?([a-zA-Z0-9]+\\(\\)?)?(?P<name>.*)\.[a-zA-Z0-9]{2,4}$", path)

    if match:

        name = match.group("name")
        log.info(f"Got name: {name}")
        return name

    else:

        log.warning("Couldn't get name from path {path}")
        return None
