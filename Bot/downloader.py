'''
Performs all download processes
'''
import logging, subprocess, os, functools
import pafy
import youtube_dl
from pydub import AudioSegment
import asyncio

log = logging.getLogger(__name__)


def download_audio_manually(url: str) -> None:
    '''
    Download audio via youtube-dl
    '''

    log.info("Downloading audio via youtube-dl")

    # Set youtube-dl settings
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': "./temp/%(title)s.%(ext)s",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '192'
        }]
    }

    # Download audio
    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def normalizeAudio(audiopath: str, destination_path: str) -> int:
    '''
    Changes the volume of the track to a uniform one
    Returns the length of the track in seconds
    '''
    log.info(f"Normalizing {audiopath}")

    # Read file with pydub
    song = AudioSegment.from_file(audiopath)

    # Normalize sound
    loudness = song.dBFS
    quieterAudio = 40 + loudness
    song = song - quieterAudio

    # Export song to new path
    song.export(destination_path, 'webm')

    # Remove old track
    os.remove(audiopath)

    log.info(f"Normalized {audiopath}")

    # Return length of song
    return int(song.duration_seconds)


async def try_to_download(url: str, target: str) -> tuple:
    '''
    Downloads and normalizes audio. Returns its path and length
    '''

    # Download audio
    log.info("Starting download process")

    # Get all files in temp directory
    files = os.listdir("temp")

    try:
        # Get video details with pafy
        vid = pafy.new(url)

        # Select best audio
        bestaudio = vid.getbestaudio(preftype="webm")

        # Download video
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, functools.partial(bestaudio.download,
                                                           filepath="temp\\",
                                                           quiet=True))

    except Exception as e:

        # Download audio via youtube-dl
        log.error("Pafy failed downloading: " + str(e))
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_audio_manually, url)

    # Get path of downloaded file by getting all files in test directory
    # and removing all files that already were there
    path = list(set(os.listdir("temp")).difference(set(files)))[0]

    # Normalize volume of track, move it to the queue folder and get its length
    loop = asyncio.get_event_loop()
    length = await loop.run_in_executor(None, normalizeAudio, "temp\\" + path, target + "\\" + path)

    log.info("Finished downloading and normalizing. Path: " + str(path))

    return path, length


async def dl_captions(url: str, lang: str):
    '''
    Download captions of a video via youtube-dl and return their path
    '''

    # Get all files in captions directory
    files = os.listdir("captions")

    log.info(f"Downloading captions of {url} in {lang}")

    # Set youtube-dl settings
    ytdl_options = {
        "writesubtitles": True,
        'outtmpl': "./captions/%(title)s.%(ext)s",
        "subtitleslangs": [lang],
        "skip_download": True,
        "quiet": True
    }

    # Start download process
    with youtube_dl.YoutubeDL(ytdl_options) as ydl:
        loop = asyncio.get_event_loop()
        dl_function = functools.partial(ydl.download,
                                        [url])
        await loop.run_in_executor(None, dl_function)

    try:

        # Get path of downloaded file by getting all files in test directory
        # and removing all files that already were there
        path = list(set(os.listdir("captions")).difference(set(files)))[0]

    except IndexError:
        log.info("No captions downloaded")
        return None

    return "captions\\" + path
