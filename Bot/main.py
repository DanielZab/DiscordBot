# region imports

# High priority imports
import logging
import logger
import hide

# Audio file imports
from pydub import AudioSegment
import audioread
from pydub.utils import which

# Environment variables
from dotenv import load_dotenv

# Database connection
from database import DataBase

# File Manager
import file_manager

# Control board commands
import control

# Other imports
import lyricsgenius, psutil, asyncio, subprocess, youtube_dl

# Standard library imports
import os, shutil, datetime, sys, random, time, math, re

# Google and Discord api imports
import discord
from discord.ext import tasks, commands
from discord_slash import SlashCommand, SlashContext, manage_components, ComponentContext, ButtonStyle
from youtube import YouTube
from typing import Union

# Import logger
log = logging.getLogger(__name__)
log.info("All modules have been imported")
# endregion


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
    '''
    Extends the discord.Client class in order to add some custom properties
    '''

    def __init__(self) -> None:

        super().__init__()
        self.setup()
    
    def setup(self):
        
        # Create containers for current voice channel and its name
        self.channel = None
        self.vc = None

        # Create counter for current track
        self.queue_counter = 1

        # Indicates if all requested songs have been played
        self.waiting = True

        # Lock which guarantees exclusive access to a shared resource
        self.lock = asyncio.Lock()

        # To download in between of songs
        self.placeholders = []

        # A list of emojis representing numbers
        self.emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🚫']

        # Container for all emojis
        self.custom_emojis = dict()

        # Indicates how long a song has been played
        self.song_duration = 0


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


async def check_channel(ctx: SlashContext) -> bool:

    # Check whether user is in a voice channel
    if not (ctx.author.voice and ctx.author.voice.channel):

        log.info(f"{ctx.author} is not in a voice channel")
        await ctx.send("You are not in a voice channel", hidden=True)

        return False

    log.info(f"{ctx.author} is in a voice channel")
    return True


async def join(ctx: SlashContext) -> bool:

    global client

    log.info("Trying to join a voice channel")
    if not await check_channel(ctx):

        return False

    channel = ctx.author.voice.channel

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


def download_audio(url) -> None:

    # Download audio into specific test folder
    output = subprocess.run(f'youtube-dl -F {url}', capture_output=True).stdout
    log.info(output.decode("utf-8"))
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


def get_length(url, convert=True) -> int:
    '''
    Gets length of video using youtube-dl
    '''

    log.info(f"Getting length of {url}")
    # Get length in format hh:mm:ss
    output = subprocess.run(f'youtube-dl -o "./test/%(title)s.%(ext)s" --get-duration {url}', capture_output=True).stdout
    result = output.decode("utf-8")

    log.info("Result lenght: {result}")

    if convert:
        # Convert to seconds
        match = re.match(r"^((?P<h>\d{1,2}(?=\S{4,6})):)?((?P<m>\d{1,2}):)?(?P<s>\d{1,2})$", result)
        hours = int(match.group("h") or 0)
        minutes = int(match.group("m") or 0)
        seconds = int(match.group("s") or 0)
        result = hours * 3600 + minutes * 60 + seconds
    
    return result

def convert_url(url: str, id_only: bool = False) -> str:
    '''
    Convert youtube url to a uniform format
    '''

    log.info("Converting url")
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


def song_done(error: Exception) -> None:
    '''
    Callback function which gets calles after a song has ended
    Prints errors if present and starts the next track
    '''
    global client

    if error:
        log.error("An error has occurred during playing: " + str(error))
    else:
        log.info("The song has ended")

    client.queue_counter += 1

    # Play next track
    check_player.start()


def get_emojis() -> None:
    '''
    Gets custom emojis for certain methods
    '''

    global client

    # Get control board emojis if available and named correctly
    emoji_list = client.emojis

    # Define defaults
    rewind, play, forward, back, stop, skip = "⏪", "⏯", "⏩", "⏮", "⏹", "⏭"

    for emoji in emoji_list:
        if emoji.name == "botRewind":
            rewind = emoji
        if emoji.name == "botPlay":
            play = emoji
        if emoji.name == "botForward":
            forward = emoji
        if emoji.name == "botBack":
            back = emoji
        if emoji.name == "botStop":
            stop = emoji
        if emoji.name == "botSkip":
            skip = emoji

    client.custom_emojis["rewind"] = rewind
    client.custom_emojis["play"] = play
    client.custom_emojis["forward"] = forward
    client.custom_emojis["back"] = back
    client.custom_emojis["stop"] = stop
    client.custom_emojis["skip"] = skip


async def add_to_queue(ctx: SlashContext, url: str, index: int = 0, update: int = 0) -> bool:
    '''
    Downloads audio and adds it to the queue
    '''

    global db, client

    # Block all processes but one
    await client.lock.acquire()

    # Try to download
    try:

        # Check if video is longer than 10 minutes
        temp_length = get_length(url)
        if temp_length > 600 and not client.waiting and not update:

            # Download audio later
            await ctx.send("The video is longer than 10 minutes, I'll download it after the current track", hidden=True)
            path = "Placeholder"
            length = temp_length
            log.info(f"Video length exceeds 10 minutes: {length / 60}")

        else:

            # Get all files in test directory
            files = os.listdir("test")

            # Download audio
            log.info("Starting download process")
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, download_audio, url)
            log.info("Finished downloading")

            # Get path of downloaded file by getting all files in test directory
            # and removing all files that already were there
            path = list(set(os.listdir("test")).difference(set(files)))[0]
            log.info(f"Path found: {str(path)}")
            
            # Normalize volume of track, move it to the queue folder and get its length  
            length = await loop.run_in_executor(None, normalizeAudio, "test\\" + path, "queue\\" + path)

    except Exception as e:

        log.error("Failed downloading. Error: " + str(e))

        client.lock.release()

        return False

    # Move all entries higher or equal to index
    if index:

        index += client.queue_counter

        db.move_entries(index)

    client.lock.release()

    if update:

        db.execute(f"UPDATE queuelist SET path='{path}' WHERE id={update}")

        return True

    else:
        # Insert track details into database/queuelist
        db.insert_into_queue(index, url, length, path)

    if path == "Placeholder":

        _id = int(db.execute(f"SELECT id FROM queuelist WHERE index = {index}")[0][0])
        client.placeholders.append((ctx, url, _id))

    if client.waiting:

        client.waiting = False

        check_player.start()

    return True


async def play_audio(ctx: SlashContext, url: str, index: int) -> None:

    if url:

        # Check if url is valid
        try:
            url = convert_url(url)

        except ValueError:
            await ctx.send("Invalid url")
            return

        # Download audio
        await ctx.send("Downloading audio", hidden=True)

        if await add_to_queue(ctx, url, index):

            await ctx.send("Added to the queue")

        else:

            await ctx.send("Something went wrong")

    else:

        await ctx.send("Something went wrong, sorry :(")


@slash.subcommand(base="play", subcommand_group='video', name="by_name")
async def play_by_name(ctx: SlashContext, name: str, amount: int = 1, index: int = 0) -> None:
    '''
    Performs a youtube search with the given keywords and plays its audio
    '''

    # Join channel
    if not await join(ctx):

        return

    # Check if number of videos to search is below zero
    if amount < 1:

        await ctx.send("Very funny!")

    elif amount == 1:

        # Perform youtube search
        url = yt.get_search(name)[0]

        await play_audio(ctx, url, index)

    else:

        await ctx.send("Searching", hidden=True)
        global client
        # Limit amount to 9
        amount = 9 if amount > 9 else amount

        # Get list of youtube urls
        urls = yt.get_search(name, amount=amount)

        # Create message
        msg = "These are the results:"
        for i, url in enumerate(urls):

            # Get length of video
            length = get_length(url, convert=False).replace("\n", "")

            #Get id of video
            _id = convert_url(url, id_only=True)

            # Get name of video
            title = yt.get_name(_id)

            msg += f"\n\t{i + 1}: {title} ({length})"
        
        message = await ctx.send(msg)

        # Add reactions so the member can choose a song
        for i in range(amount):
            await message.add_reaction(client.emoji_list[i])
        
        # Add the cancel emoji
        await message.add_reaction(client.emoji_list[-1])

        # Define criteria that must be met for the reaction to be accepted
        def check(r, u):
            log.info(f"Got response: {str(r)}. ({str(r) in client.emoji_list}, {ctx.author.id == u.id}, {r.message.id == message.id})")
            return str(r) in client.emoji_list and ctx.author.id == u.id and r.message.id == message.id

        # Wait for reaction
        try:

            log.info("Waiting for reaction")
            reaction, user = await client.wait_for('reaction_add', check=check, timeout=200)
        
        except TimeoutError:

            log.warning("No reaction has been made")
            return

        log.info(f"Rection received: {reaction} by {user}")
        
        # Get index of emoji in emoji_list
        emoji_index = client.emoji_list.index(str(reaction))

        # Check if it is the cancel emoji
        if emoji_index == len(client.emoji_list) - 1:

            await ctx.send("Download was cancelled")
            return

        video = urls[emoji_index]

        log.info(f"{video} was chosen")

        await play_audio(ctx, video, index)
        # TODO Index must not be higher than max queue_id


@slash.subcommand(base="play", subcommand_group='video', name="by_url")
async def play_by_url(ctx: SlashContext, url: str, index: int = 0) -> None:
    '''
    Plays the youtube video with the corresponding url
    '''

    # Join channel
    if not await join(ctx):

        return

    await play_audio(ctx, url, index)


@slash.slash(name="control")
async def _control(ctx: SlashContext):
    '''
    Opens the control panel
    '''

    global client

    await ctx.defer()

    buttons_1 = [
        manage_components.create_button(
            style=ButtonStyle.blurple,
            emoji=client.custom_emojis["rewind"],
            custom_id="rewind"
        ),
        manage_components.create_button(
            style=ButtonStyle.green,
            emoji=client.custom_emojis["play"],
            custom_id="play_pause_toggle"
        ),
        manage_components.create_button(
            style=ButtonStyle.blurple,
            emoji=client.custom_emojis["forward"],
            custom_id="fast_forward"
        ),
    ]
    buttons_2 = [
        manage_components.create_button(
            style=ButtonStyle.blue,
            emoji=client.custom_emojis["back"],
            custom_id="back"
        ),
        manage_components.create_button(
            style=ButtonStyle.red,
            emoji=client.custom_emojis["stop"],
            custom_id="stop"
        ),
        manage_components.create_button(
            style=ButtonStyle.blue,
            emoji=client.custom_emojis["skip"],
            custom_id="skip"
        ),
    ]

    action_row_1 = manage_components.create_actionrow(*buttons_1)
    action_row_2 = manage_components.create_actionrow(*buttons_2)

    await ctx.send("Control board", components=[action_row_1, action_row_2])


@slash.slash(name="skip")
async def _skip(ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:
    global client, db
    await control_board.skip(client, db, ctx, amount=amount)


@slash.slash(name="back")
async def _back(ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:
    global client, db
    await control_board.back(client, db, ctx, amount=amount)


@slash.slash(name="pause")
async def _pause(ctx: Union[SlashContext, ComponentContext]) -> None:
    global client, db
    await control_board.pause(client, db, ctx)


@slash.slash(name="fast_forward")
async def _fast_forward(ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:
    global client, db
    await control_board.fast_forward(client, db, ctx, amount=amount)


@slash.slash(name="rewind")
async def _rewind(ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:
    global client, db
    await control_board.rewind(client, db, ctx, amount=amount)


@slash.slash(name="stop")
async def _stop(ctx: Union[SlashContext, ComponentContext]):
    global client, db
    await control_board.stop(ctx)

@client.event
async def on_ready() -> None:
    print(f'{client.user} has connected to Discord!')

    # Delete all tracks from previous uses
    file_manager.reset_directories()

    if env_var.AUTO_HIDE == 'True':

        hide.hide()
    
    get_emojis()

    update_duration.start()
    # TODO:Change status


@client.event
async def on_component(ctx: ComponentContext):

    global client, db

    log.info(f"Received component input with id: {ctx.custom_id}")

    # Assign a function to every custom_id
    buttons = {
        "skip": control_board.skip,
        "fast_forward": control_board.fast_forward,
        "stop": control_board.stop,
        "back": control_board.back,
        "rewind": control_board.rewind,
        "play_pause_toggle": control_board.pause
    }

    # Get function from custom_id of component
    try:
        function = buttons[ctx.custom_id]

    except Exception as e:
        log.error("No function assigned! " + str(e))
        await ctx.send("Something went wrong!", hidden=True)
        return
    
    await function(client, db, ctx)

@tasks.loop(count=1)
async def check_player() -> None:
    '''
    Plays the next track, if all conditions are met
    '''

    global client, db

    log.info("Checking whether to play audio")

    # Check whether connected to voice client
    if client.vc:

        # Check whether previous song has ended
        if client.vc.is_playing() or client.vc.is_paused():

            log.warning("check_player was called although song hasn't ended yet")

            return

        # Download placeholders
        if len(client.placeholders) > 0:
            for ctx, url, _id in client.placeholders:
                await add_to_queue(ctx, url, index=0, update=_id)
                await ctx.send("Your previous track was downloaded")

        # Get index of last song in queuelist
        query = "SELECT MAX(queue_id) FROM queuelist;"
        index = db.execute(query)[0][0]
    
        # Check if more songs are available
        if index and index >= client.queue_counter:
            
            # Get and play next song
            while True:
                try:
                    path = db.execute(f"SELECT path FROM queuelist WHERE queue_id = {client.queue_counter}")[0][0]
                    break
                except IndexError:
                    client.queue_counter += 1
                
            source = discord.FFmpegOpusAudio('queue\\' + path)

            # Reset song timer
            client.song_duration = 0

            # Play song
            client.vc.play(source, after=song_done)

            # Stop waiting if was waiting
            client.waiting = False

        else:

            log.info(f"No more tracks available! Current index: {index}")

            # Wait for next track
            client.waiting = True


@tasks.loop(seconds=0.5)
async def update_duration():

    global client

    # Add half a second to the duration timer if the player is currently playing
    if client.vc and client.vc.is_playing():
        client.song_duration += 0.5

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

    # Create control board commands manager
    control_board = control.ControlBoard()

    # TODO Create directories

    # Run Discord Bot
    client.run(env_var.TOKEN)
