import logging, subprocess, os, functools
import pafy
import youtube_dl
from pydub import AudioSegment
import asyncio
import functools

from youtube_dl.compat import _TreeBuilder
log = logging.getLogger(__name__)


def download_audio_manually(url) -> None:

    # Download audio into specific test folder
    output = subprocess.run(f'youtube-dl -F {url}', capture_output=True).stdout
    log.debug(output.decode("utf-8"))
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': "./temp/%(title)s.%(ext)s",
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'm4a',
            'preferredquality': '192'
        }]
    }

    with youtube_dl.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    #msg = f'youtube-dl -o "./test/%(title)s.%(ext)s" --extract-audio --format best {url}'
    #os.system(msg)


def normalizeAudio(audiopath: str, destination_path: str) -> None:
    '''
    Changes the volume of the track to a uniform one
    Returns the length of the track in seconds
    '''
    log.info(f"Normalizing {audiopath}")
    # Get song with pydub
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
    return song.duration_seconds


async def try_to_download(url: str, target: str) -> tuple:
    '''
    Downloads and normalizes audio
    '''

    # Download audio
    log.info("Starting download process")

    # Get all files in temp directory
    files = os.listdir("temp")

    try:
        # TODO Multiprocessing
        vid = pafy.new(url)
        bestaudio = vid.getbestaudio(preftype="webm")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, functools.partial(bestaudio.download,
                                                           filepath="temp\\",
                                                           quiet=True))

    except Exception as e:

        log.error("Pafy failed downloading: " + str(e))
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_audio_manually, url)
    
    # Get path of downloaded file by getting all files in test directory
    # and removing all files that already were there
    path = list(set(os.listdir("temp")).difference(set(files)))[0]
    log.info(f"Path found: {str(path)}")
    
    # Normalize volume of track, move it to the queue folder and get its length
    loop = asyncio.get_event_loop()

    length = await loop.run_in_executor(None, normalizeAudio, "temp\\" + path, target + "\\" + path)

    path = target + r"\\" + path

    log.info("Finished downloading")

    return path, length


async def dl_captions(url: str, lang: str):

    files = os.listdir("captions")
    loop = asyncio.get_event_loop()

    log.info("Downloading captions")
    ytdl_options = {
        "writesubtitles": True,
        'outtmpl': "./captions/%(title)s.%(ext)s",
        "subtitleslangs:": [lang],
        "skip_download": True,
        "quiet": True
    }
    with youtube_dl.YoutubeDL(ytdl_options) as ydl:
        dl_function = functools.partial(ydl.download,
                                        [url])
        await loop.run_in_executor(None, dl_function)
    
    try:
        path = list(set(os.listdir("captions")).difference(set(files)))[0]
    
    except IndexError:
        ytdl_options = {
        "writeautomaticsub": True,
        'outtmpl': "./captions/%(title)s.%(ext)s",
        "subtitleslangs:": [lang],
        "skip_download": True,
        "quiet": True
        }
        with youtube_dl.YoutubeDL(ytdl_options) as ydl:
            dl_function = functools.partial(ydl.download,
                                            [url])
            await loop.run_in_executor(None, dl_function)
        
        try:
            path = list(set(os.listdir("captions")).difference(set(files)))[0]
        
        except:
            return None

    return "captions\\" + path
