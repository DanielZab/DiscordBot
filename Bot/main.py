'''
Launches bot and manages commands
'''
# region imports

# High priority imports
import enum
import logger
import hide

# Environment variables
from env_vars import EnvVariables

# Database connection
from database import Database

# File manager
import file_manager

# Music downloader
from downloader import try_to_download

# Converter
from converter import convert_time, convert_url, get_name_from_path

# MyClient class
from my_client import MyClient

# String creator
import string_creator

# Lyrics skript
import lyrics

# Control board commands
import control

# Performance checker
from per_check import PerfCheck

# Updating slash commands
import slashcommands

# Standard library imports
import random

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


def check_index(index: int) -> int:
    '''
    Checks if given index is higher than the index of the last
    song in queue, and returns 0 if that is the case.
    Otherwise returns given value without any changes.
    The returned value ought to be set as the new index
    Songs with an index of 0 will be added at the end of the queue
    '''

    # Check if index is higher than index of last song in queue
    if index > db.get_max_queue_id() - client.queue_counter:

        log.info("Index too high!")
        return 0

    return index


def check_playlist_name(name: str) -> bool:
    '''
    Determines whether given name value is an existing playlist directory
    and returns the corresponding boolean
    '''

    # Check if any playlist directory matches given value
    if any(name == e for e in file_manager.get_playlists()):
        return True

    log.info("Passed not existing playlist name: " + str(name))
    return False


async def check_admin(ctx: SlashContext) -> bool:
    '''
    Checks if a user has admin permissions and returns the corresponding boolean
    '''

    log.info(f"Checking admin permissions of {ctx.author}")

    # Check if user is admin or has admin role
    if ctx.author.guild_permissions.administrator or (client.admin_role_id and any(client.admin_role_id == role.id for role in ctx.author.roles)):

        log.info(f"{ctx.author} is an admin")

        return True

    log.info(f"{ctx.author} is not an admin")
    await ctx.send("You are not allowed to perform this action!")

    return False


async def check_channel(ctx: SlashContext) -> bool:
    '''
    Checks whether user is in a voice channel and returns the corresponding bool
    '''

    # Check if user is connected to a voice channel
    if not (ctx.author.voice and ctx.author.voice.channel):

        log.info(f"{ctx.author} is not in a voice channel")
        await ctx.send("You are not in a voice channel", hidden=True)

        return False

    log.info(f"{ctx.author} is in a voice channel")
    return True


async def join(ctx: SlashContext) -> bool:
    '''
    Ensures that bot joins the voice channel of the user, if he is connected to a channel
    '''

    log.info("Trying to join a voice channel")

    # Check if user is connected to a voice channel
    if not await check_channel(ctx):

        return False

    # Get voice channel of user
    channel = ctx.author.voice.channel

    # Check if bot is already in a voice channel
    if client.channel:

        # Move to the requested channel if in wrong channel
        if client.channel != ctx.author.voice.channel:

            log.info("Moving from current channel")
            await client.channel.move_to(channel)

        else:

            log.info("Already in channel")

    # Otherwise connect to channel where the user is located
    else:

        try:

            # Connect to channel
            log.info("Joining channel")
            await channel.connect(reconnect=True, timeout=90)
        
        except Exception as e:

            log.error("Couldn't connect to voice channel " + str(e))

    # Check whether procedure was successful
    if channel == client.voice_clients[0].channel:

        log.info("Connected to voice channel")

        # Assign current voice channel to the bot
        client.channel = channel
        client.vc = client.voice_clients[0]

        return True

    # Error detection
    log.error(f"Failed to connect. Channel={channel}, "
              "vc={client.voice_clients[0]}")
    await ctx.send("Something went wrong :/", hidden=True)

    return False


async def add_to_queue(url: str, index: int = 0, file_data: Union[bool, dict] = False, dl: bool = False, length: int = 0) -> bool:
    '''
    Collects song data and adds audio to queuelist
    Parameters:
        url: youtube url of the song
        index: position of song in queuelist
        file_data: Data of file, if song was downloaded previously (In playlists)
        dl: Indicates whether download file if all criteria are met
        length: Passes length of song if already known
    Returns name of added video
    '''

    log.info("Adding to queuelist")

    # Check if file data was passed
    if not file_data:

        # Get missing file data
        path = ''
        if not length:
            _id = convert_url(url, id_only=True)
            length = await yt.get_length(_id)

        assert length

        # Check if video qualifies for download: dl parameter must be true and 
        # total video length may not exceed 90 seconds
        if dl and length < 60 * 1.5:

            # Download video and set path
            path, length = await try_to_download(url, 'queue')
            path = r'queue\\' + path

    else:

        # Get data from previously downloaded file
        path = file_data["path"]
        length = file_data["length"]

    # Set index to zero if below zero
    if index < 0:
        index = 0

    # Move all entries higher or equal to index
    if index:

        # Convert index to position in queue
        index += client.queue_counter

        # Move entries
        db.move_entries(index)

    # Try to get the name from file path
    name = get_name_from_path(path)

    # Check if name was found
    if not name:
        
        # Get name via youtube data api
        name = await yt.get_name(convert_url(url, id_only=True))

    # Insert song data into queue
    log.info(f"Inserting into queue {index}, {url}, {length}, {path}, {name}")
    db.insert_into_queue(index, url, length, path, name)

    # Start player if no song is playing
    if client.waiting:

        client.waiting = False

        client.start_player()

    # Return song name
    return name


async def play_audio(ctx: SlashContext, url: str, index: int) -> None:
    '''
    Checks if url and index are valid and calls add_to_queuelist afterwards.
    Updates queue list messages at the end
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
        result = await add_to_queue(url, index=index, dl=True)
        await ctx.send(f"{result} was added to the queue")

    except Exception as e:

        await ctx.send("Something went wrong")
        log.error("Couldn't add to queuelist " + str(e))
    
    # Update queue list messages
    await client.update_queuelist_messages()


@slash.slash(name="play")
async def _play(ctx: SlashContext, name: str = None, url: str = None, amount: int = 1, index: int = 0) -> None:
    '''
    Plays video either by its url, or by the results from a youtube query
    If neither name nor url was passed, just starts player
    '''

    await ctx.defer()

    # Join channel
    if not await join(ctx):

        return

    # Play url if given
    if url:
        await play_audio(ctx, url, index)
    
    # Check if song title was passed
    elif name:

        # Check if number of videos to search is below zero
        if amount < 1:

            await ctx.send("Very funny!")

        # Check if 1 result was requested
        elif amount == 1:

            # Perform youtube search
            url = await yt.get_search(name)

            # Play first result
            url = url[0]
            assert url
            await play_audio(ctx, url, index)
        
        else:

            await ctx.send("Searching", hidden=True)

            # Limit amount to 9
            amount = 9 if amount > 9 else amount

            # Get list of youtube urls
            _ids = await yt.get_search(name, amount=amount, full_url=False)

            # Get video lengths
            lengths = await yt.get_length(_ids)
            lengths = lengths[0]

            # Convert ids to youtube urls
            urls = list('https://www.youtube.com/watch?v=' + e for e in _ids)

            # Create and send message
            msg = "These are the results:"
            for i in range(len(_ids)):

                # Convert length of video
                _time = list(convert_time(lengths[i]))
                _time = (str(e) for e in _time)
                length = ":".join(_time)

                # Remove hours if video length less than one hour
                if length.startswith("0:") and len(length) > 4:
                    length = length[2:]

                # Get name of video
                title = await yt.get_name(_ids[i])

                # Append video data to message
                msg += f"\n\t{i + 1}: {title} ({length})"
            
            msg = await ctx.send(msg)

            # Add reactions in order to let the user choose a song
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

            # Select correct url
            video = urls[emoji_index]

            log.info(f"{video} was chosen")

            await play_audio(ctx, video, index)

    else:
        
        # Starting player
        client.start_player(force=True)


@slash.slash(name="playlist")
async def _playlist(ctx: SlashContext, url: str = None, name: str = None, index: int = 0, limit: int = 0, randomize: bool = False):
    '''
    Adds videos of a playlist to the queue
    If name was passed will add the corresponding in playlists directory
    Otherwise will play the playlist from its url
    '''

    # Check if either url or name have been given
    if not (name or url):
        await ctx.send("Please specify a name or url!")

    await ctx.defer()

    # Join channel
    if not await join(ctx):

        return

    # Check whether to play a downloaded playlist
    if name:

        # Check if playlist exists
        if not check_playlist_name(name):
            await ctx.send("This playlist does not exist")
            return

        # Get playlist details
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
            await add_to_queue(song[0], index=index, file_data=song_data)

            # Increase index by one if active
            if index:
                index += 1

        # Update queue list message
        await client.update_queuelist_messages()

        await ctx.send("Playlist added")
    
    # Check if url was passed
    elif url:

        # Check if url is valid and extract id
        try:
            url = convert_url(url, id_only=True, playlist=True)
        
        except ValueError:

            await ctx.send("Invalid url")

            return
        
        await ctx.send("Preparing playlist", hidden=True)

        # Get ids of playlist videos
        _ids = await yt.get_playlist_contents(url, full_url=False)

        # Shuffle list if desired
        if randomize:

            random.shuffle(_ids)

        # Shorten the list
        if limit and limit < len(_ids):

            _ids = _ids[:limit]

        # Get video lengths
        lengths = await yt.get_length(_ids)

        assert lengths
        
        # Remove all invalid video ids
        for invalid_video in lengths[1]:
            _ids.remove(invalid_video)

        lengths = lengths[0]
        
        # If index is too high, set to 0
        # This adds the song to the end of the queue
        index = check_index(index)

        # Convert ids to urls
        urls = list('https://www.youtube.com/watch?v=' + e for e in _ids)

        for i, song_url in enumerate(urls):

            try:
                # Add song to queue
                await add_to_queue(song_url, index=index, length=lengths[i])

                # Start player if music player not active
                if client.waiting:
                    client.start_player()
                    client.waiting = False

                # Increase index if given
                if index:
                    index += 1

            except Exception as e:

                log.error(f"Couldn't add {song_url} to playlist: " + str(e))

        # Update queue list messages
        await client.update_queuelist_messages()
        await ctx.send("All songs from playlist have been added")


@slash.slash(name="control")
async def _control(ctx: SlashContext):
    '''
    Sends a message containing the most important music player functions as buttons
    '''

    await ctx.defer()

    # Define button details
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

    # Convert buttons to action row elements
    action_row_1 = manage_components.create_actionrow(*buttons_1)
    action_row_2 = manage_components.create_actionrow(*buttons_2)

    # Create and send embed
    embed = discord.Embed()
    embed.title = "No Current Track"

    msg = await ctx.send(embed=embed, components=[action_row_1, action_row_2])

    # Add message to control board message list
    client.control_board_messages.append(msg)

    # Delete old control board messages that exceed max amount
    # Current max amount is 1
    while len(client.control_board_messages) > 1:
        old_msg = client.control_board_messages.pop(0)
        try:
            await old_msg.delete()
        except:
            log.error("Couldn't delte old client board message")


@slash.slash(name="skip")
async def _skip(ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:
    '''
    Calls skip method of ControlBoard class
    '''

    await control_board.skip(ctx, amount=amount)


@slash.slash(name="back")
async def _back(ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:
    '''
    Calls back method of ControlBoard class
    '''

    await control_board.back(ctx, amount=amount)


@slash.slash(name="pause")
async def _pause(ctx: Union[SlashContext, ComponentContext]) -> None:
    '''
    Calls pause method of ControlBoard class
    '''

    await control_board.pause(ctx)


@slash.slash(name="fast_forward")
async def _fast_forward(ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:
    '''
    Calls fast forward method of ControlBoard class
    '''

    await control_board.fast_forward(ctx, amount=amount)


@slash.slash(name="rewind")
async def _rewind(ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:
    '''
    Calls rewind method of ControlBoard class
    '''

    await control_board.rewind(ctx, amount=amount)


@slash.slash(name="stop")
async def _stop(ctx: Union[SlashContext, ComponentContext]):
    '''
    Calls stop method of ControlBoard class
    '''

    await control_board.stop(ctx)


@slash.slash(name="queue")
async def _queue(ctx: SlashContext, amount: int = 10):
    '''
    Creates a queue list message
    '''

    await ctx.defer()

    # Get the queue list database entries
    query = f"SELECT name, length FROM queuelist WHERE queue_id >= {client.queue_counter} ORDER BY queue_id"
    queuelist = db.execute(query)

    # Check if queue list is empty
    if len(queuelist) < 1:
        queuelist_strings = ["No songs in queue!"]

    # Create message strings
    else:
        queuelist_strings = string_creator.create_queue_string(queuelist, amount)

    sent_messages = []

    # Send messages
    for string in queuelist_strings:
        if string:
            sent_message = await ctx.send(string)
            sent_messages.append(sent_message)
    
    # Add message to list, so it can be updated in the future
    client.queuelist_messages.append([sent_messages, amount])

    # Delete all old messages that exceed max amount
    # Current max amount is 1
    while len(client.queuelist_messages) > 1:
        log.info("Deleting old queuelist message")
        old_messages = client.queuelist_messages.pop(0)
        for msg in old_messages[0]:
            try:
                await msg.delete()
            except:
                log.error("Failed to delete old queue list message")


@slash.slash(name="quit")
async def _quit(ctx: SlashContext):
    '''
    Closes all tasks, resets data and terminates programm
    '''

    # Check for admin permissions
    if not await check_admin(ctx):
        return
    
    await ctx.defer()

    # Cancel update duration loop
    client.update_duration.cancel()

    # Disconnect from voice channel, reset queuelist table and delete files
    await control_board.stop(ctx, silent=True)

    # Set status to offline
    await client.change_presence(status=discord.Status.offline)

    await ctx.send("Bye!")

    # Stop bot
    try:
        await client.close()
    except RuntimeError:
        log.info("Runtime error while closing bot")

    log.info("Bot was closed")


@slash.subcommand(base="create", name="playlist")
async def _create_playlist(ctx: SlashContext, url: str, name: str) -> None:
    '''
    Creates a playlist directory and downloads playlist contents
    '''

    try:
    
        # Check if user has admin permissions
        if not await check_admin(ctx):
            return

        await ctx.defer()

        # Check if url is valid and extract id
        try:
            _id = convert_url(url, id_only=True, playlist=True)
        
        except ValueError:

            await ctx.send("Invalid url")
            return

        # Create playlist directory
        try:
            name = file_manager.create_playlist_directory(name)
        
        except ValueError:
            await ctx.send("Invalid playlist name")
            raise Exception
        
        except FileExistsError:
            await ctx.send("This playlist already exists")
            return

        # Create database table
        try:
            db.create_playlist_table(name, url)
        
        except Exception as e:
            log.info("Couldn't create table: " + str(e))
            raise Exception
        
        # Add choice to slash command
        slashcommands.update_playlist_commands()

        # Get urls of videos in playlist
        url_list = await yt.get_playlist_contents(_id)
        
        # Stop music player by force
        client.stop(force=True)

        # Create message which indicates download progress
        playlist_msg = await ctx.send(string_creator.create_playlist_download_string("Downloading contents", 0, url_list))

        # Download contents
        for i, url in enumerate(url_list):
            try:
                await client.lock.acquire()

                # Update progress
                try:
                    cont = string_creator.create_playlist_download_string("Downloading contents", i, url_list)
                    await playlist_msg.edit(content=cont)
                except Exception as e:
                    log.warning("Couldn't update message: " + str(e))
                
                # Download audio
                path, length = await try_to_download(url, "playlists\\" + name)

                # Change path to queue directory
                path = r"playlists\\" + name + r"\\" + path

                # Insert audio data into playlist database table
                db.insert_into_playlist(name, url, path, int(length))

                log.info(f"{path} added to {name} playlist")
            
            except Exception as e:
                log.error(f"Couldn't add {url} to playlist. Error: " + str(e))
            
            finally:
                client.lock.release()

        await playlist_msg.edit(content="Finished creating playlist")

        # Start player
        client.start_player(force=True)
    
    except Exception as e:

        # Revert changes
        file_manager.delete_directory("playlists\\" + name)
        db.execute("DROP TABLE " + name)
        slashcommands.update_playlist_commands()

        log.error("Couldn't create playlist. Error: " + str(e))

        await ctx.send("Something went wrong")


@slash.subcommand(base="update", name="playlist")
async def _update_playlist(ctx: SlashContext, name: str, url: str = "") -> None:
    '''
    Updates an existing playlist
    '''

    await ctx.defer()

    # Check if user has admin permissions
    if not await check_admin(ctx):
        return

    # Check if playlist exists
    if not check_playlist_name(name):
        await ctx.send("Unknown playlist name")
        return

    # Stop player by force
    client.stop(force=True)

    # Check if a custom url was passed
    if not url:

        # Try to get original playlist url
        try:
            url = db.execute(f"SELECT url FROM playlists WHERE name = '{name}'")[0][0]
        except (IndexError, TypeError):
            log.error("Couldn't find playlist url")
            await ctx.send("An error occurred")
            return

    try:

        # Check whether url is a video url and convert it to a standardised format
        _id = convert_url(url)
        new_urls = set([_id])

    except ValueError:

        # Extract playlist id
        _id = convert_url(url, id_only=True, playlist=True)
        new_urls = set(await yt.get_playlist_contents(_id))

    # Get all playlist urls
    old_urls = db.execute(f"SELECT url FROM `{name}`")
    old_urls = set(e[0] for e in old_urls)

    # Determine the urls that are not yet downloaded
    urls_to_download = list(new_urls.difference(old_urls))

    # Send messages which indicates download progress
    msg = await ctx.send(string_creator.create_playlist_download_string("Updating contents", 0, urls_to_download))

    # Download songs
    for i, url_to_download in enumerate(urls_to_download):
        try:
            await client.lock.acquire()

            # Edit download progress
            await msg.edit(content=string_creator.create_playlist_download_string("Updating contents", i, urls_to_download))

            # Download song
            path, length = await try_to_download(url_to_download, "playlists\\" + name)

            # Change path to queue directory
            path = r"playlists\\" + name + r"\\" + path

            # Insert song data into playlist database table
            db.insert_into_playlist(name, url, path, int(length))

            log.info(f"{path} added to {name} playlist")

        except Exception as e:
            log.error(f"Couldn't add {url} to playlist. Error: " + str(e))

        finally:
            client.lock.release()
        
    await msg.edit(content="Finished updating playlist")
    client.start_player(force=True)


@slash.subcommand(base="delete", name="playlist")
async def _delete_playlist(ctx: SlashContext, name: str) -> None:
    '''
    Deletes a playlist
    '''

    await ctx.defer()

    # Check if user has admin permissions
    if not await check_admin(ctx):
        return
    
    # Check if playlist exists
    if not check_playlist_name(name):

        await ctx.send("Unknown playlist!")

        # Update playlist command in case slash command options are outdated
        slashcommands.update_playlist_commands()
        return

    # Stop player by force
    client.stop(force=True)

    # Delete playlist files
    file_manager.delete_directory("playlists\\" + name)

    # Update slash commands
    slashcommands.update_playlist_commands()

    # Close gaps in queue list
    db.reset_queuelist_ids()

    # Delete database table and entries
    db.execute(f"DROP TABLE {name}")
    db.execute(f"DELETE FROM playlists WHERE name = {name}")

    # Start music player again
    client.start_player(force=True)

    await ctx.send(name + " was deleted")

@slash.slash(name="repeat")
async def _repeat(ctx: SlashContext, amount: int = -1) -> None:
    '''
    Repeats the current song amount times.
    Repeats indefinitely if amount has a negative value
    '''

    # Check whether to stop repeating song
    if client.repeat and amount < 1:
        
        # Stop repeating song
        client.stop_repeat()
    
        await ctx.send(f"I won't repeat {client.current_track_name} anymore")

    else:
        
        # Start repeating
        client.start_repeat(amount)

        # Determine which message to send
        if amount > 0:
            msg = f"I will repeat {client.current_track_name} {amount} times"
        else:
            msg = f"I will repeat {client.current_track_name} indefinitely"

        await ctx.send(msg)


@slash.slash(name="shuffle")
async def _shuffle(ctx: SlashContext) -> None:
    '''
    Shuffles queue list
    '''

    log.info("Shuffling playlist")

    await ctx.defer()

    # Get all next tracks
    query = f"SELECT id FROM queuelist WHERE queue_id > {client.queue_counter}"
    queuelist = db.execute(query)

    # Shuffle queue
    random.shuffle(queuelist)

    # Assign videos to their new position
    for i, entry in enumerate(queuelist):
        query = f"UPDATE queuelist SET queue_id = {i + client.queue_counter} WHERE id = {entry[0]}"
        db.execute(query)
    
    # Update queue list messages
    await client.update_queuelist_messages()

    await ctx.send("The queuelist has been shuffled")


@slash.slash(name="lyrics")
async def _lyrics(ctx: SlashContext, full=False):
    '''
    Tries to get and send lyrics
    '''

    await ctx.defer()

    # Get the url of the current video
    url = db.get_current_url(client.queue_counter)

    # Return if not playing anything
    if not url:
        await ctx.send("No song playing!")
        return

    # Extract video id
    _id = convert_url(url, id_only=True)

    # Check whether to send all lyrics at once
    if full:

        # Get lyrics from genius library
        current_lyrics = await lyrics.get_genius_lyrics(_id, env_var)

        # Return if no lyrics found
        if not current_lyrics:
            await ctx.send("Could't find lyrics")
            return

        # Convert lyrics to a printable format
        msg_list = string_creator.create_genius_lyrics_message(current_lyrics)

        # Send all created messages
        for msg in msg_list:
            await ctx.send(msg)

    # Else send lyrics in sync with song
    else:

        # Try to get lyrics
        current_lyrics = await lyrics.get_lyrics(ctx, _id, client, yt, env_var)

        # Check if lyrics source is the geniuslyrics api
        if current_lyrics[0] == "genius":

            # Convert lyrics to a printable format
            msg_list = string_creator.create_genius_lyrics_message(current_lyrics[1])

            # Send all messages
            for msg in msg_list:
                await ctx.send(msg)
        
        # Check if request was cancelled
        elif current_lyrics[0] == "cancelled":

            await ctx.send("Download was cancelled")

        # Check if no lyrics were found
        elif all(not e for e in current_lyrics):
            await ctx.send("Couldn't find lyrics")

        else:

            # Reset lyrics index
            # The lyrics index indicates which verse is the current one
            client.current_lyrics_index = 1

            # Convert lyrics to a printable format
            client.current_lyrics = lyrics.create_lyrics_list(*current_lyrics)

            # Send message
            msg = await ctx.send("Loading lyrics", components=[client.lyrics_action_row])

            # Add message to lyrics message list
            client.lyrics_messages.append(msg)

            # Delete all old messages that exceed max amount
            # Current max amount is 1
            while len(client.lyrics_messages) > 1:
                old_msg = client.lyrics_messages.pop(0)
                try:
                    await old_msg.delete()
                except:
                    log.error("Couldn't delete old lyrics message")
                log.info(str(old_msg) + " was deleted")


@client.event
async def on_ready() -> None:
    '''
    Performs the startup preperations
    '''

    # Delete all tracks from previous uses
    file_manager.reset_directories()

    # Set admin role
    client.admin_role_id = env_var.ADMIN_ROLE_ID

    if env_var.AUTO_HIDE == 'True':

        console_visibility.hide()

    # Get custom emojis
    client.get_emojis()

    await client.change_presence(status=discord.Status.online)

    print(f'{client.user} has connected to Discord!')


@client.event
async def on_component(ctx: ComponentContext):
    '''
    Handles component interactions
    '''

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

    # Determine whether to increase or reduce lyrics timer
    # The lyrics timer attempts to correct the time difference
    # between the played song and its lyrics
    if ctx.custom_id == "reduce_lyrics_timer":
        client.lyrics_timer -= 1
        await ctx.send("Decreased", delete_after=1.5)

    elif ctx.custom_id == "increase_lyrics_timer":
        client.lyrics_timer += 1
        await ctx.send("Increased", delete_after=1.5)

    # Check whether to show full lyrics
    elif ctx.custom_id == "show_full_lyrics":
        await client.show_full_lyrics(ctx)

    # Otherwise assign control board function
    else:
    
        # Get function from custom_id of component
        try:
            function = buttons[ctx.custom_id]

        except Exception as e:
            log.error("No function assigned! " + str(e))
            await ctx.send("Something went wrong!", hidden=True)
            return
        
        # Call assigned functions
        await function(ctx)


if __name__ == "__main__":

    # Create DataBase class instance
    db = Database(env_var.SQL_USER, env_var.SQL_PW)
    db.setup()

    # Create YouTube class instance
    yt = YouTube(env_var.DEVELOPER_KEY)

    # Create connection to lyricsgenius api
    genius = lyricsgenius.Genius(env_var.GENIUS_TOKEN)

    # Create control board commands manager
    control_board = control.ControlBoard(client, db)

    # Create performance checker
    perf_check = PerfCheck()

    # Create visibility manager
    console_visibility = hide.console

    # Store database in client class
    client.set_db(db)

    # Run Discord Bot
    client.run(env_var.TOKEN)

# TODO implement cogs
# TODO setup
# TODO visibility control
# TODO volume control
# TODO playlists for each server seperately
