# region imports
# High priority imports
import logging
import logger
import hide

# Standard library imports
import os, shutil, datetime, sys, random, time, math, re

# Google and Discord api imports
import discord
from discord.ext import tasks, commands
from discord_slash import SlashCommand, SlashContext
from youtube import YouTube


# Audio file imports
from pydub import AudioSegment
import audioread
from pydub.utils import which

# Environment variables
from dotenv import load_dotenv

# Database connection
from database import DataBase

# Multiprocessing
import multi

# Other imports
import lyricsgenius, psutil, asyncio

# endregion

# Import logger
log = logging.getLogger(__name__)
log.info("All modules have been imported")


# region classes
class EnvVariables():
    '''
    Container for all environment variables
    '''
    def __init__(self) -> None:
        load_dotenv()
        # load all environment variables
        self.GENIUS_TOKEN = os.getenv('GENIUS_ACCESS_TOKEN')
        self.TOKEN = os.getenv('DISCORD_TOKEN')
        self.DEVELOPER_KEY = os.getenv('YOUTUBE_API_KEY')
        self.AUTO_HIDE = os.getenv('AUTO_HIDE')
        self.SQL_USER = os.getenv('MYSQL_USER')
        self.SQL_PW = os.getenv('MYSQL_PW')


class AudioFile:
    '''
    Stores data of a single audio file
    '''
    def __init__(self,
                 name: str,
                 url: str,
                 length,
                 path: str,
                 downloaded: bool,
                 id: int,
                 queue_id: int,
                 boption) -> None:
        self.name = name
        self.url = url
        self.length = length
        self.path = path
        self.downloaded = downloaded
        self.boption = boption
        self.id = id
        self.queue_id = int


class MyClient(discord.Client):
    def __init__(self) -> None:
        super().__init__()

        # Create containers for current voice channel and its name
        self.channel = None
        self.vc = None

        # Create counter for current track
        self.queue_counter = 1

        # Indicator whether new song can be played
        self.done = True
# endregion


# Assign slash command client
client = MyClient()
slash = SlashCommand(client)


async def check_admin(ctx: SlashContext) -> bool:
    '''
    Checks if a user has admin permissions
    '''

    log.info(f"Checking admin permissions of {ctx.author}")

    if ctx.author.guild_permissions.administrator:
        log.info(f"{ctx.author} is an admin")

        return True

    log.info(f"{ctx.author} is not an admin")

    await ctx.send("You are not allowed to perform this action!")
    return False


async def join(ctx: SlashContext) -> bool:
    global client

    log.info("Trying to join a voice channel")

    # Check whether user is in a voice channel
    if ctx.author.voice and ctx.author.voice.channel:
        channel = ctx.author.voice.channel
    else:
        log.info(f"{ctx.author} is not in a voice channel")
        await ctx.send("You are not in a voice channel", hidden=True)

        return False

    # Check if bot is already in a voice channel
    if client.channel:

        # Move to the requested channel if in wrong channel
        if client.channel != ctx.author.voice.channel:
            log.info("Moving from current channel")
            await client.channel.move_to(channel)
        else:
            log.info("Already in channel")
    else:

        # Join channel
        log.info("Joining channel")
        await channel.connect(reconnect=True, timeout=90)

    # Check whether procedure was successful
    if channel == client.voice_clients[0].channel:
        log.info("Connected to voice channel")

        # Assign current voice channel to the bot
        client.channel = channel
        client.vc = client.voice_clients[0]

        return True

    log.error(f"Failed to connect. Channel={channel}, "
              "vc={client.voice_clients[0]}")
    await ctx.send("Something went wrong :/", hidden=True)

    return False


def download_audio(url) -> bool:

    # download audio into specific directory as a 
    msg = f'youtube-dl -o "./test/%(title)s.%(ext)s" --extract-audio {url}'
    os.system(msg)


def add_to_queue(url, index=0) -> None:
    
    global db
    
    # Try downloading
    try:
        log.info("Starting download process")
        multi.start_process(download_audio, (url,))
        log.info("Finished downloading")

    except Exception as e:
        log.error("Failed downloading. Error: " + str(e))
        return False

    if index:
        
        index += client.queue_counter

        #Move queue_id of all tracks past the most recent one
        move_entries(index)

    insert_into_queue(index, url)


def move_entries(index) -> None:

    global db
    db.execute(" ".join(["UPDATE queuelist",
                         "SET queue_id = queue_id + 1",
                         f"WHERE queue_id >= {index};"]))

def insert_into_queue(index, url) -> None:

    global db
    if not index:
        query = "SELECT MAX(queue_id) FROM queuelist;"
        if query:
            index = 1 + db.exeute(query)[0][0]
        else:
            index = 1
    
    path = os.listdir("test")[0]
    length = normalizeAudio("\\test\\" + path, "\\queue\\" + path)
    path = "\\queue\\" + path
    db.add_to_queue(index, url, path, length)

def normalizeAudio(audiopath, destination_path) -> int:

    # Get song with pydub
    song = AudioSegment.from_file(audiopath)

    # Normalize sound
    loudness = song.dBFS
    quieterAudio = 40 + loudness
    song = song - quieterAudio

    # Export song to new path
    match = re.search(r"\.(?P<ending>[a-zA-Z0-9]+)$", audiopath)
    song.export(destination_path, match.group('ending'))

    # Return length of song
    return song.duration_seconds

def song_done(error):
    global client
    if error:
        log.error("An error has occurred during playing: " + str(e))
    else:
        log.info("The song has ended")
    client.done = False

@slash.subcommand(base="play", subcommand_group='video', name="by_name")
async def play_by_name(ctx: SlashContext, name, amount=1):
    '''
    Plays music
    '''

    # Check if user is an admin
    if not await check_admin(ctx):
        return

    #Join channel
    if not await join(ctx):
        return

    # Check amount of videos
    if amount < 1:
        await ctx.send("Very funny!")

    elif amount == 1:
        
        # Get url
        url = yt.get_search(name)[0]
        if url:

            # Download audio in a multiprocess
            await ctx.send("Downloading audio", hidden=True)
            if add_to_queue(url):
                await ctx.send("Added to the queue")
            else:
                await ctx.send("Something went wrong")

            #TODO play audio and add track to queuelist

        else:
            await ctx.send("Something went wrong, sorry :(")


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    # TODO:Delete past tracks
    if env_var.AUTO_HIDE == 'True':
        hide.hide()
    check_player.start()
    # TODO:Change status


@tasks.loop(seconds=1)
async def check_player():
    global client, db
    log.info("Checking whether to play audio")
    if client.done and client.vc:
        if client.vc.is_playing() or client.vc.is_paused():
            return
        query = "SELECT MAX(queue_id) FROM queuelist;"
        index = db.execute(query)[0][0]
        if not index or index >= client.queue_counter:
            path = db.execute(f"SELECT path FROM queuelist WHERE queue_id = {client.queue_counter}")[0][0]
            source = discord.FFmpegOpusAudio(path)
            client.vc.play(source, after=song_done)
            client.queue_counter += 1


if __name__ == "__main__":

    # Get environment variables
    env_var = EnvVariables()

    # Create DataBase class instance
    db = DataBase(env_var.SQL_USER, env_var.SQL_PW)
    db.setup()

    # Create YouTube class instance
    yt = YouTube(env_var.DEVELOPER_KEY)

    # Create connection to lyricsgenius api
    genius = lyricsgenius.Genius(env_var.GENIUS_TOKEN)

    # Run Discord Bot
    client.run(env_var.TOKEN)
