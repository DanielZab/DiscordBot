# region imports

# High priority imports
import logger
import hide

from discord import embeds
from discord_slash.model import SlashMessage

# Audio file imports
from pydub import AudioSegment
import audioread
from pydub.utils import which

# Environment variables
from env_vars import EnvVariables

# Database connection
from database import DataBase

# File manager
import file_manager

# Music downloader
from downloader import normalizeAudio, try_to_download

# Converter
from converter import convert_time, convert_url, format_time_ffmpeg, get_name_from_path

# MyClient class
from my_client import MyClient

# String creator
import string_creator

# Lyrics skript
import lyrics

# Control board commands
import control

# Updating slash commands
import slashcommands

# Standard library imports
import os, shutil, datetime, sys, random, time, math, re

# Google and Discord api imports
import discord
from discord.ext import tasks, commands
from discord_slash import SlashCommand, SlashContext, manage_components, ComponentContext, ButtonStyle
from youtube import YouTube

# Other imports
import lyricsgenius, psutil, asyncio, subprocess, youtube_dl
from typing import Union


# Import logger
import logging
log = logging.getLogger(__name__)
log.info("All modules have been imported")
# endregion


# Assign slash command client
client = MyClient()
slash = SlashCommand(client)


# Get environment variables
env_var = EnvVariables()


def get_length(url, convert=True) -> Union[int, str]:
    '''
    Gets length of video using youtube-dl in seconds unless convert is False
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


def check_index(index) -> int:

    if index > db.get_max_queue_id() - client.queue_counter:

        log.info("Index too high!")
        return 0

    return index


async def check_admin(ctx: SlashContext) -> bool:
    '''
    Checks if a user has admin permissions
    '''

    log.info(f"Checking admin permissions of {ctx.author}")

    if ctx.author.guild_permissions.administrator or (client.admin_role_id and any(client.admin_role_id == role.id for role in ctx.author.roles)):

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


async def add_to_queue(ctx: SlashContext, url: str, index: int = 0, file_data: Union[bool, dict] = False, dl: bool = False) -> bool:
    '''
    Adds audio to queuelist
    '''

    # Check if file data was passed
    if not file_data:

        # Get missing file data
        path = ''
        length = get_length(url)

        if dl and length < 60 * 4:
            path, length = await try_to_download(url, 'queue')

    else:

        # Get data from previously downloaded file
        path = file_data["path"]
        length = file_data["length"]

    # Move all entries higher or equal to index
    if index:

        index += client.queue_counter

        db.move_entries(index)

    name = get_name_from_path(path)

    if not name:
        name = yt.get_name(convert_url(url, id_only=True))

    db.insert_into_queue(index, url, length, path, name)

    if client.waiting:

        client.waiting = False

        client.check_player.start()
    
    await client.update_queuelist_messages()

    return yt.get_name(convert_url(url, id_only=True))


async def play_audio(ctx: SlashContext, url: str, index: int) -> None:
    '''
    Checks if url is valid and adds the track to the queuelist
    '''

    # Check if url is valid
    try:
        url = convert_url(url)

    except ValueError:

        await ctx.send("Invalid url")
        return

    # If index is too high, set to 0
    # This adds the song to the end of the queue
    index = check_index(index)

    # Add to queuelist
    try:
        result = await add_to_queue(ctx, url, index, dl=True)
        await ctx.send(f"{result} was added to the queue")

    except Exception as e:

        await ctx.send("Something went wrong")
        log.error("Couldn't add to queuelist " + str(e))


@slash.slash(name="play")
async def _play(ctx: SlashContext, name: str = None, url: str = None, amount: int = 1, index: int = 0) -> None:
    '''
    Performs a youtube search with the given keywords and plays its audio
    '''

    await ctx.defer()

    # Join channel
    if not await join(ctx):

        return

    # Play url if given
    if url:
        await play_audio(ctx, url, index)
    
    elif name:

        # Check if number of videos to search is below zero
        if amount < 1:

            await ctx.send("Very funny!")

        elif amount == 1:

            # Perform youtube search
            url = await yt.get_search(name)
            url = url[0]

            await play_audio(ctx, url, index)

        else:

            await ctx.send("Searching", hidden=True)

            # Limit amount to 9
            amount = 9 if amount > 9 else amount

            # Get list of youtube urls
            urls = await yt.get_search(name, amount=amount)

            # Create message
            msg = "These are the results:"
            for i, url in enumerate(urls):

                # Get length of video
                length = get_length(url, convert=False).replace("\n", "")

                # Get id of video
                _id = convert_url(url, id_only=True)

                # Get name of video
                title = yt.get_name(_id)

                msg += f"\n\t{i + 1}: {title} ({length})"
            
            msg = await ctx.send(msg)

            # Add reactions so the member can choose a song
            for i in range(amount):
                await msg.add_reaction(client.emoji_list[i])
            
            # Add the cancel emoji
            await msg.add_reaction(client.emoji_list[-1])

            # Define criteria that must be met for the reaction to be accepted
            def check(r, u):
                log.info(f"Got response: {str(r)}. ({str(r) in client.emoji_list}, {ctx.author.id == u.id}, {r.message.id == msg.id})")
                return str(r) in client.emoji_list and ctx.author.id == u.id and r.message.id == msg.id

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

    else:
        
        # Starting music, if there is any
        client.start_player()


@slash.slash(name="playlist")
async def _playlist(ctx: SlashContext, url: str = None, name: str = None, index: int = 0, limit: int = 0, randomize: bool = False):

    # Check if either url or name have been given
    if not (name or url):
        await ctx.send("Please specify a name or url!")

    await ctx.defer()

    # Join channel
    if not await join(ctx):

        return

    if name:

        query = f"SELECT url, path, length FROM {name}"
        playlist_songs = db.execute(query)

        # Shuffle list if desired
        if randomize:

            random.shuffle(playlist_songs)

        # Shorten the list
        if limit and limit < len(playlist_songs):

            playlist_songs = playlist_songs[:limit]

        # If index is too high, set to 0
        # This cause the songs to be added the end of the queue
        index = check_index(index)
        for song in playlist_songs:
            
            # Put song data into a dictionary
            song_data = {
                "path": song[1].replace("\\", "\\\\"),
                "length": song[2]
            }

            # Add song to queue
            await add_to_queue(ctx, song[0], index=index, file_data=song_data)

            # Increase index by one if active
            if index:
                index += 1

        await ctx.send("Playlist added")
    
    elif url:

        # Check if url is valid and extract id
        try:
            url = convert_url(url, id_only=True, playlist=True)

        except ValueError:

            await ctx.send("Invalid url")

            return

        await ctx.send("Preparing playlist", hidden=True)

        urls = await yt.get_playlist_contents(url)

        # Shuffle list if desired
        if randomize:

            random.shuffle(urls)

        # Shorten the list
        if limit and limit < len(urls):

            urls = urls[:limit]
        
        # If index is too high, set to 0
        # This adds the song to the end of the queue
        index = check_index(index)

        for song_url in urls:

            try:
                # Add song to queue
                await add_to_queue(ctx, song_url, index=index)

                # Increase index if given
                if index:
                    index += 1

            except Exception as e:

                log.error(f"Couldn't add {url} from playlist" + str(e))

        await ctx.send("All songs from playlist have been added")

# TODO player reset/loop check

@slash.slash(name="control")
async def _control(ctx: SlashContext):
    '''
    Opens the control panel
    '''

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

    embed = discord.Embed()
    embed.title = "No Current Track"

    msg = await ctx.send(embed=embed, components=[action_row_1, action_row_2])

    client.control_board_messages.append(msg)

    # FIXME cannot load on multiple instances

    while len(client.control_board_messages) > 1:
        old_msg = client.control_board_messages.pop(0)
        await old_msg.delete()


@slash.slash(name="skip")
async def _skip(ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:

    await control_board.skip(client, db, ctx, amount=amount)


@slash.slash(name="back")
async def _back(ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:

    await control_board.back(client, db, ctx, amount=amount)


@slash.slash(name="pause")
async def _pause(ctx: Union[SlashContext, ComponentContext]) -> None:

    await control_board.pause(client, db, ctx)


@slash.slash(name="fast_forward")
async def _fast_forward(ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:

    await control_board.fast_forward(client, db, ctx, amount=amount)


@slash.slash(name="rewind")
async def _rewind(ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:

    await control_board.rewind(client, db, ctx, amount=amount)


@slash.slash(name="stop")
async def _stop(ctx: Union[SlashContext, ComponentContext]):

    await control_board.stop(client, db, ctx)


@slash.slash(name="queue")
async def _queue(ctx: SlashContext, amount: int = 10):

    await ctx.defer()

    # Get the database entries
    query = f"SELECT name, length FROM queuelist WHERE queue_id >= {client.queue_counter} ORDER BY queue_id"
    queuelist = db.execute(query)

    if len(queuelist) < 1:
        await ctx.send("No songs in queue!")
        return

    # Create message strings
    queuelist_strings = string_creator.create_queue_string(queuelist, amount)

    sent_messages = []

    # Send messages
    for string in queuelist_strings:
        sent_message = await ctx.send(string)
        sent_messages.append(sent_message)
    
    # Add message to list, so it can be updated in the future
    client.queuelist_messages.append((sent_messages, amount))

    # Delete all old messages
    while len(client.queuelist_messages) > 1:
        log.info("Deleting old queuelist message")
        old_messages = client.queuelist_messages.pop(0)
        for msg in old_messages[0]:
            await msg.delete()


@slash.slash(name="quit")
async def _quit(ctx: SlashContext):

    # Check for admin permissions
    if not await check_admin(ctx):
        return

    await ctx.defer()

    client.update_duration.cancel()

    # Disconnect from voice channel, reset queuelist table and delete files
    await control_board.stop(client, db, ctx, silent=True)

    # Set status to offline
    await client.change_presence(status=discord.Status.offline)

    await ctx.send("Bye!")

    # Stop bot
    await client.close()
    log.info("Bot was closed")


@slash.subcommand(base="create", name="playlist")
async def _create_playlist(ctx: SlashContext, url: str, name: str) -> None:

    try:

        if not await check_admin(ctx):
            return

        await ctx.defer(hidden=True)

        try:
            _id = convert_url(url, id_only=True, playlist=True)
        
        except ValueError:

            await ctx.send("Invalid url", hidden=True)
            return

        try:
            name = file_manager.create_playlist_directory(name)
        
        except ValueError:
            ctx.send("Invalid playlist name", hidden=True)
            return

        # Create database table
        try:
            db.create_playlist_table(name, url)
        
        except Exception as e:
            log.info("Couldn't create table: " + str(e))
            shutil.rmtree("playlists\\" + name)
        
        # Add choice to slash command
        slashcommands.update_playlist_commands()

        # Get urls of videos in playlist
        url_list = await yt.get_playlist_contents(_id)

        # Download contents
        await ctx.send("Downloading contents", hidden=True)

        for url in url_list:

            try:

                await client.lock.acquire()
                
                path, length = await try_to_download(url, "playlists\\" + name)

                # Change path to queue directory
                path = r"playlists\\" + name + r"\\" + path

                db.insert_into_playlist(name, url, path, int(length))

                log.info(f"{path} added to {name} playlist")
            
            except Exception as e:
                log.error(f"Couldn't add {url} to playlist. Error: " + str(e))
            
            finally:
                client.lock.release()

        await ctx.send("Finished creating playlist")
    
    except Exception as e:

        # Revert changes
        file_manager.delete_directory(name)
        db.execute("DROP TABLE " + name)

        log.error("Couldn't create playlist. Error: " + str(e))

        await ctx.send("Something went wrong")


@slash.subcommand(base="update", name="playlist")
async def _update_playlist(ctx: SlashContext, name: str, url: str = "") -> None:

    if not await check_admin(ctx):
        return

    await ctx.defer()

    if not url:
        pass
    # TODO update


@slash.subcommand(base="delete", name="playlist")
async def _delete_playlist(ctx: SlashContext, name: str) -> None:

    if not await check_admin(ctx):
        return

    await ctx.defer()

    client.stop(force=True)

    file_manager.delete_directory("playlists\\" + name)

    slashcommands.update_playlist_commands()

    db.reset_queuelist_ids()

    db.execute(f"DROP TABLE {name}")

    db.execute(f"DELETE FROM playlists WHERE name = {name}")

    client.start_player()

    await ctx.send(name + " was deleted")

@slash.slash(name="repeat")
async def _repeat(ctx: SlashContext, amount: int = -1) -> None:
    if amount > -1 and client.repeat:
        client.repeat_counter = amount
        await ctx.send(f"I will repeat {client.current_track_name} {amount} time(s)")
    elif client.repeat:
        client.repeat = False
        client.repeat_counter = -1
        await ctx.send(f"I won't repeat {client.current_track_name} anymore")
    else:
        client.repeat = True
        client.repeat_counter = amount
        await ctx.send(f"I will repeat {client.current_track_name} indefinitely")


@slash.slash(name="shuffle")
async def _shuffle(ctx: SlashContext) -> None:

    log.info("Shuffling playlist")

    await ctx.defer()

    query = f"SELECT id FROM queuelist WHERE queue_id > {client.queue_counter}"
    queuelist = db.execute(query)

    random.shuffle(queuelist)
    for i, entry in enumerate(queuelist):
        query = f"UPDATE queuelist SET queue_id = {i + client.queue_counter} WHERE id = {entry[0]}"
        db.execute(query)
    
    await client.update_queuelist_messages()
    await ctx.send("The queuelist has been shuffled")


@slash.slash(name="lyrics")
async def _lyrics(ctx: SlashContext, full=False):
    await ctx.defer()
    url = db.get_current_url(client.queue_counter)
    _id = convert_url(url, id_only=True)

    if full:

        current_lyrics = await lyrics.get_genius_lyrics(_id)
        msg_list = string_creator.create_lyrics_message(current_lyrics)

        for msg in msg_list:
            await ctx.send(msg)

    else:
        current_lyrics = await lyrics.get_lyrics(ctx, _id, client, yt)

        if current_lyrics[0] == "genius":
            msg_list = string_creator.create_lyrics_message(current_lyrics)

            for msg in msg_list:
                await ctx.send(msg)
        
        else:
            print(current_lyrics)
            lyric_point_list = lyrics.create_lyrics_list(*current_lyrics)


@client.event
async def on_ready() -> None:
    print(f'{client.user} has connected to Discord!')

    # Delete all tracks from previous uses
    file_manager.reset_directories()

    # Set admin role
    client.admin_role_id = env_var.ADMIN_ROLE_ID

    if env_var.AUTO_HIDE == 'True':

        hide.hide()

    # Get custom emojis
    client.get_emojis()

    # TODO Change status
    # TODO volume / normalize
    # TODO reset
    # TODO lyrics
    # TODO update playlist
    # TODO bugfix
    # TODO playlist private
    # TODO optimize getting data
    # TODO pause play cringe


@client.event
async def on_component(ctx: ComponentContext):

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


if __name__ == "__main__":

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
    # TODO visibility
    client.set_db(db)

    # Run Discord Bot
    client.run(env_var.TOKEN)

# TODO implement cogs
# TODO upload emojis
