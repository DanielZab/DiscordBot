'''
Contains the MyClient class
'''
from per_check import PerfCheck
import discord
from discord.ext import commands
import asyncio
import logging
import datetime
from discord_slash.model import SlashMessage
import string_creator
from discord.ext import tasks
from ytdl_source import YTDLSource
from converter import convert_url
import time, math
from discord_slash import manage_components, ButtonStyle
log = logging.getLogger(__name__)


class MyClient(commands.Bot):
    '''
    Extends the commands.Bot class in order to add some custom attributes and methods
    '''

    def __init__(self) -> None:

        super().__init__("!")
        self.setup()
    
    def setup(self) -> None:
        
        # Create containers for current voice channel and its name
        self.channel = None
        self.vc = None

        # Create instance of PerfCheck (for debugging purposes)
        self.perf = PerfCheck()

        # Container for current datetime
        self.now = datetime.datetime.now()

        # Create counter for current track index
        self.queue_counter = 1

        # Indicates if all requested songs have been played
        self.waiting = True

        # Create lock which guarantees exclusive access to a shared resource
        self.lock = asyncio.Lock()

        # A list of emojis representing numbers
        self.emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🚫']

        # Container for all emojis
        self.custom_emojis = dict()

        # Indicates how long a song has been played
        self.song_timer = 0

        # Current status
        self.current_status = None

        # Before options for the player, can specify different things such as where to start
        # or playback speed
        self.boption = None

        # Containter for all messages containing control boards
        self.control_board_messages = []

        # Container for all messages containing the queuelist
        self.queuelist_messages = []

        # Container for all lyrics messages
        self.lyrics_messages = []

        # Indicates the current line of lyrics
        self.current_lyrics_index = 0

        # The name and duration of the current track
        self.current_track_name = None
        self.current_track_duration = 0
        self.current_thumbnail = None

        # Containter for current lyrics
        self.current_lyrics = []

        # Container for the id of the admin role
        self.admin_role_id = None

        # Indicates if player is not enableable currently
        # Is set to True when creating, updating or deleting playlists
        self.force_stop = False

        # Indicates whether to repeat current song
        self.repeat = False

        # How often to repeat current song
        # When negative, will repeat indefinitely
        self.repeat_counter = -1

        # Import emojis
        self.get_emojis()
        
        # Create buttons actions row for messages containing the lyrics
        buttons = [
            manage_components.create_button(
                style=ButtonStyle.blue,
                label="-1",
                custom_id="reduce_lyrics_timer"
            ),
            manage_components.create_button(
                style=ButtonStyle.red,
                label="Show full",
                custom_id="show_full_lyrics"
            ),
            manage_components.create_button(
                style=ButtonStyle.blue,
                label="+1",
                custom_id="increase_lyrics_timer"
            ),
        ]
        self.lyrics_action_row = manage_components.create_actionrow(*buttons)

        # Balances the time difference between the song and its lyrics
        self.lyrics_timer = 0

        # Start update duration loop
        self.update_duration.cancel()
        self.update_duration.start()

    def vc_check(self) -> bool:
        '''
        Checks whether player is paused/playing a song
        '''
        return self.vc and (self.vc.is_paused() or self.vc.is_playing())
    
    def play_with_boption(self, boption: str) -> None:
        '''
        Resets the current track with the boption settings
        '''

        # Check if playing music currently
        if self.vc_check():
        
            # Reduce queue counter by one
            self.queue_counter -= 1

            # Assign boptions to self
            self.boption = boption

            # Restart player
            self.vc.stop()
            return True
        
        else:
            return False

    def start_player(self, force: bool = False) -> None:

        '''
        Starts player
        '''
        # Make player enableable again
        if force:
            self.force_stop = False

        # Wait until previous check_player loops are finished
        self.check_player.stop()
        while self.check_player.is_running():
            time.sleep(0.05)
        
        # Start player
        self.check_player.start()
    
    def stop(self, force: bool = False):
        '''
        Stops player
        '''

        # Check whether to make player not enableable temporarily
        if force:
            log.info("Forcing music stop")
            self.force_stop = True

        # Stop player, if playing music
        if self.vc_check():
            log.info("Stopping music")
            self.vc.stop()

    def reset_current_song_data(self) -> None:
        '''
        Resets data about current song
        '''

        self.current_track_name = None
        self.current_track_duration = 0
        self.current_thumbnail = None
    
    def set_db(self, db) -> None:
        '''
        Stores a Database object
        '''
        self.db = db
    
    def song_done(self, error: Exception) -> None:
        '''
        Callback function which gets called after a song has ended
        Prints errors if present and starts the next track
        '''

        # Check if player currently disabled
        if self.force_stop:
            log.warning("Force stop")
            self.queue_counter -= 1
            return
        
        # Report errors
        elif error:
            log.error("An error has occurred during playing: " + str(error))

        else:
            log.info("The song has ended")

        # Increase queue counter if currently not repeating
        if not self.repeat:
            self.queue_counter += 1

        # Check if number of repeats is definite
        elif self.repeat_counter > -1:

            # Check whether to stop repeating
            if self.repeat_counter == 0:
                self.repeat = False
                self.repeat_counter = -1
            
            # Otherwise reduce the number of remaining repeats by one
            else:
                self.repeat_counter -= 1

        # Play next track
        self.start_player()
    
    def get_emojis(self) -> None:
        '''
        Gets custom emojis for certain methods
        '''

        # Get control board emojis if available and named correctly
        emoji_list = self.emojis

        # Define defaults
        rewind, play, forward, back, stop, skip = "⏪", "⏯", "⏩", "⏮", "⏹", "⏭"

        # Search list of custom emojis for control board icons
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

        # Assign results to custom emojis dict
        self.custom_emojis["rewind"] = rewind
        self.custom_emojis["play"] = play
        self.custom_emojis["forward"] = forward
        self.custom_emojis["back"] = back
        self.custom_emojis["stop"] = stop
        self.custom_emojis["skip"] = skip

    def reset_player(self) -> None:
        '''
        Gets called when player needs to be reset from check_player.
        Since start_player method waits for the termination of the check_player loop execution,
        calling start_player in check_player would result in an endless loop. 
        Hence, reset_player method and the reset_player_loop act as a workaround,
        because starting the reset_player_loop, which calls start_player afterwards,
        does not prevent check_player from terminating.
        '''

        self.reset_player_loop.start()
    
    def stop_repeat(self) -> None:
        '''
        Stops the repetition of current song
        '''
        self.repeat = False
        self.repeat_counter = -1

    def start_repeat(self, amount: int) -> None:
        '''
        Starts the repetition of the current song.
        The song willbe repeated amount of times, 
        if amount is negative will repeat indefinitely
        '''

        self.repeat = True
        self.repeat_counter = amount

    async def update_queuelist_messages(self) -> None:
        '''
        Updates the messages displaying the queue list
        Queue list messages may consist of more than one message,
        if their length is above 20 entries. These are referred to as
        queue list chains
        '''

        log.info("Updating queuelists")

        # Get current and all next songs
        query = f"SELECT name, length FROM queuelist WHERE queue_id >= {self.queue_counter} ORDER BY queue_id"
        queuelist = self.db.execute(query)

        # Delete all messages if there are no more songs
        if len(queuelist) < 1:

            log.info("No more songs, deleting all queuelist messages")
            for messages in self.queuelist_messages:

                for message in messages[0]:
                    if message in messages:
                        messages.remove(message)
                    try:
                        await message.delete()
                    except discord.errors.NotFound:
                        log.warning("Couldn't delete queue list message")

            return

        # Update all messages
        for messages, amount in self.queuelist_messages:

            log.info(f"Updating queuelist message of length {amount}")

            # Create queue list message string
            new_messages = string_creator.create_queue_string(queuelist, amount)

            # Loop through all messages of queue list chain
            for i in range(len(messages)):

                try:
                    
                    # Update message
                    await messages[i].edit(content=new_messages[i])

                except IndexError:
                    
                    # Delete this and all following messages in queue list chain
                    for j in range(i, len(messages)):
                        await messages[j].delete()
                    messages = messages[:i]
                    log.warning(f"Deleted {j-i} queuelist messages")
                    break
                
                except discord.errors.NotFound:

                    log.warning("Could not update queuelist message, it was not found")
                    messages.remove(messages[i])
    
    async def delete_queuelist_messages(self) -> None:
        '''
        Deletes all messages displaying the queue list
        Queue list messages may consist of more than one message,
        if their length is above 20 entries. These are referred to as
        queue list chains
        '''

        log.info("Deleting all queuelist messages")

        # Delete all messages
        for message_list in self.queuelist_messages:

            # Delete all messages in queue list chain
            for msg in message_list[0]:
                try:
                    await msg.delete()
                except Exception as e:
                    log.error("Couldn't delete control board message. Error: " + str(e))
    
        self.queuelist_messages = []
    
    async def delete_control_board_messages(self) -> None:
        '''
        Deletes all messages containing the control board messages
        '''

        for message in self.control_board_messages:
            try:
                await message.delete()
            except Exception as e:
                log.error("Couldn't delete control board message " + str(e))
        
        self.control_board_messages = []
    
    async def delete_lyrics_messages(self) -> None:
        '''
        Deletes all messages containing the control board messages
        '''

        for message in self.lyrics_messages:
            try:
                await message.delete()
            except Exception as e:
                log.error("Couldn't delete lyrics message " + str(e))
        
        self.lyrics_messages = []
        self.current_lyrics = []
        self.current_lyrics_index = 0
    
    async def update_control_board_messages(self):
        '''
        Updates all messages displaying the control board
        A control board message consists of a the current track name,
        a progress bar and 6 buttons for controlling the player
        '''

        # Create string
        new_embed = string_creator.create_control_board_message_embed(
            name=self.current_track_name,
            song_timer=int(self.song_timer),
            track_duration=int(self.current_track_duration),
            url=self.current_thumbnail
        )

        # Update all messages
        for msg in self.control_board_messages:
            
            # Get content of old message
            old_fields = msg.embeds[0].fields
            
            # Get content of new message
            new_fields = new_embed.fields

            # Check if message needs to be updated
            if len(old_fields) != len(new_fields) or not all(old_fields[e].value == new_fields[e].value for e in range(len(old_fields))):
                try:

                    # Update message
                    await msg.edit(embed=new_embed)

                except discord.errors.NotFound:

                    # Remove non-existent message from control board messages list
                    log.warning("Control board message not found")
                    if msg in self.control_board_messages:
                        self.control_board_messages.remove(msg)
    
    async def update_lyrics(self):
        '''
        Updates lyrics in sync with music
        '''
        
        # Increase verse index if necessary
        while self.current_lyrics_index < len(self.current_lyrics) - 1 and self.current_lyrics[self.current_lyrics_index + 1].seconds <= self.song_timer + self.lyrics_timer:
            self.current_lyrics_index += 1
        
        # Decrease verse index if necessary
        while self.current_lyrics_index > 0 and self.current_lyrics[self.current_lyrics_index - 1].seconds >= self.song_timer + self.lyrics_timer:
            self.current_lyrics_index -= 1
        
        # Create lyrics message strings
        new_msg = string_creator.create_current_lyrics_message(self.current_lyrics, self.current_lyrics_index)

        # Update all messages
        for msg in self.lyrics_messages:
            try:
                if msg.content != new_msg:
                    await msg.edit(content=new_msg)
            except Exception as e:
                log.error("Couldn't edit lyrics. " + str(e))

    async def show_full_lyrics(self, ctx):
        '''
        Prints all lyrics at once, not in sync with music
        '''

        log.info("Printing full lyrics")

        # Convert lyrics into multiple string, each containing at most 20 verses
        final_list = []
        start_index = 0
        while len(self.current_lyrics[start_index:]) > 20:
            final_list.append(self.current_lyrics[start_index: start_index + 20])
            start_index += 20
        final_list.append(self.current_lyrics[start_index:])

        # Send message
        for entry in final_list:
            msg = "\n".join(list(e.text for e in entry))
            await ctx.send(msg)
        
        # Delete all messages in sync with music
        await self.delete_lyrics_messages()

    async def update_status(self):
        '''
        Displays current track in status
        '''

        # Check if status has to be updated
        if self.current_status != self.current_track_name:

            # Check if currently playing a song
            if self.current_track_name:
                
                # Update status
                log.info("Updating status")
                status = discord.Game(self.current_track_name)
                await self.change_presence(activity=status)
            else:

                # Delete status
                log.info("Deleting status")
                await self.change_presence(activity=None)
            
            # Update current status variable
            self.current_status = self.current_track_name

    async def disconnect(self):
        '''
        Disconnects from voice channel
        '''

        if self.vc:
            await self.vc.disconnect()

    @tasks.loop(count=1)
    async def check_player(self) -> None:
        '''
        Makes various preparations, checks if new music can be played and starts player
        '''

        log.info("Checking whether to play audio")

        # Store current track for comparison later
        old_track_name = self.current_track_name

        # Check whether connected to voice and whether player is not disabled
        if self.vc and not self.force_stop:

            # Bypass steps if boption is available,
            # since its safe to assume that a track is currently playing
            # if a before option was passed
            # Before options contain ffmpeg data e.g. from which timestamp to start song
            # Boptions are used when rewinding or fast forwarding song
            if not self.boption:

                # Check whether previous song has ended
                if self.vc.is_playing() or self.vc.is_paused():

                    log.warning("Check_player was called although song hasn't ended yet")

                    return

                # Get index of last song in queuelist
                index = self.db.get_max_queue_id()
        
            # Check if more songs are available. Bypass if boption available
            if self.boption or (index and index >= self.queue_counter):
                
                # Search in database until next song is found
                # Loop process until found, to prevent errors from gaps in database
                while True:
                    try:
                        
                        # Get song with current index
                        db_result = self.db.execute(f"SELECT path, length, url, name FROM queuelist WHERE queue_id = {self.queue_counter}")
                        path = db_result[0][0]
                        url = db_result[0][2]
                        break

                    except IndexError:

                        # Increase index by 1 and repeat process
                        log.warning("Gap in queue_id list!")
                        self.queue_counter += 1
                
                # Check whehter to play a song that hasn't been downloaded
                if path == '':
                    try:

                        # Check if there are any before options
                        if self.boption:

                            # Get audio source though youtube-dl and pass before options
                            source = await YTDLSource.from_url(url, loop=self.loop, before_options=self.boption, stream=True)

                        else:

                            # Get audio source though youtube-dl without before options
                            source = await YTDLSource.from_url(url, loop=self.loop, stream=True)

                    except Exception as e:

                        # Reset player, since song can't be played
                        log.error("Couldn't get source of song " + str(e))
                        self.reset_player()
                        self.queue_counter += 1
                        return

                # Otherwise play music from a downloaded file
                else:

                    log.info("Playing downloaded song")

                    # Check if there are any before options
                    if self.boption:

                        # Get audio source and pass before options
                        source = discord.FFmpegOpusAudio(
                            path,
                            before_options=self.boption
                        )
                        log.info("Boptions loaded")

                    else:

                        # Get audio source without any additional before options
                        source = discord.FFmpegOpusAudio(path)
                
                # Delete boptions, as they won't be needed anymore
                self.boption = False

                # Reset song timer
                self.song_timer = 0

                # Wait half a second
                await asyncio.sleep(0.5)

                # Start player
                log.info("Playing song")
                self.vc.play(source, after=self.song_done)

                # Save current datetime
                self.now = datetime.datetime.now()

                # Stop waiting if was waiting
                self.waiting = False

                # Get current track name and duration
                self.current_track_name = db_result[0][3]
                self.current_track_duration = db_result[0][1]

                # Set track thumbnail
                _id = convert_url(db_result[0][2], id_only=True)
                self.current_thumbnail = f"https://i.ytimg.com/vi/{_id}/mqdefault.jpg"

            else:

                log.info(f"No more tracks available! Current index: {index}, current queuecounter: {self.queue_counter}")

                # Wait for next track
                self.waiting = True

                # Empty current song data
                self.reset_current_song_data()

                # Update control board message
                await self.update_control_board_messages()
            
            # Update queue list messages
            await self.update_queuelist_messages()
            
            # Delete lyrics messages if a new song is playing
            if len(self.lyrics_messages) > 0 and self.current_track_name != old_track_name:
                await self.delete_lyrics_messages()
            
        elif self.force_stop:
            log.warning("Player currently stopped")

        else:
            log.warning("Not connected to voice channel")

        # Update status to current song
        await self.update_status()
        
    @tasks.loop(seconds=0.1)
    async def update_duration(self):
        '''
        Gets called ten times a second to update song timer
        and check if any messages need to be updated
        '''

        # Check if playing music
        if self.vc and self.vc.is_playing():

            # Add time passed between previous loop und current time
            # to the song timer
            dif = datetime.datetime.now() - self.now
            self.song_timer += dif.seconds + dif.microseconds / 1000000

            # Store current datetime
            self.now = datetime.datetime.now()
    
            # Check if current track name is available and
            # if song timer has recently hit a new second
            if self.current_track_name and self.song_timer - math.floor(self.song_timer) < 0.15:
                
                # Check if any control board messages exist
                if len(self.control_board_messages):

                    # Update control board messages
                    await self.update_control_board_messages()
            
            # Update lyrics if there are any lyrics messages
            if len(self.lyrics_messages):
                await self.update_lyrics()
            
    @tasks.loop(count=1)
    async def reset_player_loop(self):
        '''
        Gets called when player needs to be reset from check_player loop.
        Since start_player method waits for the termination of the check_player loop execution,
        calling start_player in check_player would result in an endless loop.
        Hence, the reset_player method and the reset_player_loop act as a workaround,
        as starting the reset_player_loop, which calls start_player afterwards,
        does not prevent check_player from terminating.
        '''
        self.start_player()
