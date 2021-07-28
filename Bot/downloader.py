import logging, subprocess, os, functools
import pafy
import youtube_dl
from pydub import AudioSegment
import asyncio
log = logging.getLogger(__name__)


def download_audio_manually(url) -> None:

    # Download audio into specific test folder
    output = subprocess.run(f'youtube-dl -F {url}', capture_output=True).stdout
    log.debug(output.decode("utf-8"))
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': "./test/%(title)s.%(ext)s",
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


def multiprocess() -> None:
    pass


async def try_to_download(url: str) -> None:

    # Download audio
    log.info("Starting download process")

    try:
        # TODO Multiprocessing
        vid = pafy.new(url)
        bestaudio = vid.getbestaudio(preftype="webm")

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, functools.partial(bestaudio.download,
                                                           filepath="test\\",
                                                           quiet=True))

    except Exception as e:

        log.error("Pafy failed downloading: " + str(e))
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, download_audio_manually, url)

    log.info("Finished downloading")
