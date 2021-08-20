import discord
from discord.ext import commands
import asyncio
import logging

from discord_slash.model import SlashMessage
import string_creator
from discord.ext import tasks
from ytdl_source import YTDLSource
from converter import convert_url
log = logging.getLogger(__name__)


class MyClient(commands.Bot):
    '''
    Extends the commands.Bot class in order to add some custom properties
    '''

    def __init__(self) -> None:

        super().__init__("!")
        self.setup()
    
    def setup(self) -> None:
        
        # Create containers for current voice channel and its name
        self.channel = None
        self.vc = None

        # Create counter for current track
        self.queue_counter = 1

        # Indicates if all requested songs have been played
        self.waiting = True

        # Lock which guarantees exclusive access to a shared resource
        self.lock = asyncio.Lock()

        # A list of emojis representing numbers
        self.emoji_list = ['1️⃣', '2️⃣', '3️⃣', '4️⃣', '5️⃣', '6️⃣', '7️⃣', '8️⃣', '9️⃣', '🚫']

        # Container for all emojis
        self.custom_emojis = dict()

        # Indicates how long a song has been played
        self.song_timer = 0 

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
        self.current_lyrics_index = 1

        # The name and duration of the current track
        self.current_track_name = None
        self.current_track_duration = 0
        self.current_thumbnail = None

        # Containter for current lyrics
        self.current_lyrics = None

        # Container for the id of the admin role
        self.admin_role_id = None

        # Indicates whether player is paused manually
        self.force_stop = False

        # Indicates whether to repeat current song
        self.repeat = False

        # How often to repeat current song
        # When negative, will repeat indefinitely
        self.repeat_counter = -1

        self.get_emojis()

        self.update_duration.stop()
        self.update_duration.start()

    def vc_check(self) -> bool:
        '''
        Checks whether player is paused/playing a song
        '''
        return self.vc and (self.vc.is_paused() or self.vc.is_playing())
    
    def play_with_boption(self, boption) -> None:
        '''
        Resets the current track with the boption settings
        '''

        if self.vc_check():
        
            self.queue_counter -= 1
            self.boption = boption
            self.vc.stop()
            return True
        
        else:
            return False

    def start_player(self):

        self.force_stop = False

        self.check_player.stop()
        self.check_player.start()
    
    def stop(self, force: bool = False):

        if force:
            log.info("Forcing music stop")
            self.force_stop = True

        if self.vc_check():
            log.info("Stopping music")
            self.vc.stop()

    def reset_current_song_data(self) -> None:

        self.current_track_name = None
        self.current_track_duration = 0
        self.current_thumbnail = None
    
    def set_db(self, db) -> None:
        self.db = db
    
    def song_done(self, error: Exception) -> None:
        '''
        Callback function which gets calles after a song has ended
        Prints errors if present and starts the next track
        '''
        if self.force_stop:
            log.warning("Force stop")
            self.queue_counter -= 1
        elif error:
            log.error("An error has occurred during playing: " + str(error))
        else:
            log.info("The song has ended")

        if not self.repeat:
            self.queue_counter += 1
        elif self.repeat_counter > -1:
            if self.repeat_counter == 0:
                self.repeat = False
                self.repeat_counter = -1
            else:
                self.repeat_counter -= 1

        # Play next track
        self.check_player.stop()
        self.check_player.start()
    
    def get_emojis(self) -> None:
        '''
        Gets custom emojis for certain methods
        '''

        # Get control board emojis if available and named correctly
        emoji_list = self.emojis

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

        self.custom_emojis["rewind"] = rewind
        self.custom_emojis["play"] = play
        self.custom_emojis["forward"] = forward
        self.custom_emojis["back"] = back
        self.custom_emojis["stop"] = stop
        self.custom_emojis["skip"] = skip

    async def update_queuelist_messages(self) -> None:

        log.info("Updating queuelists")

        query = f"SELECT name, length FROM queuelist WHERE queue_id >= {self.queue_counter} ORDER BY queue_id"
        queuelist = self.db.execute(query)

        # Delete all messages if there are no more songs
        if len(queuelist) < 1:

            log.info("No more songs, deleting all queuelist messages")
            for messages in self.queuelist_messages:

                for message in messages[0]:

                    await message.delete()

            return

        for messages, amount in self.queuelist_messages:

            new_messages = string_creator.create_queue_string(queuelist, amount)

            for i, message in enumerate(messages):

                try:

                    await message.edit(content=new_messages[i])

                except IndexError:

                    await message.delete()
                
                except discord.errors.NotFound:

                    log.warning("Could not update queuelist message, it was not found")
    
    async def delete_queuelist_messages(self):

        log.info("Deleting all queuelist messages")

        for message_tuple in self.queuelist_messages:
            for msg in message_tuple[0]:
                try:
                    await msg.delete()
                except Exception as e:
                    log.error("Couldn't delete control board message. Error: " + str(e))
    
    async def delete_control_board_messages(self):

        for message in self.control_board_messages:
            await message.delete()
    
    async def delete_lyrics_messages(self):

        for message in self.lyrics_messages:
            await message.delete()
        
        self.current_lyrics = []
    
    async def send_updated_control_board_messages(self):
        # Create string
        new_embed = string_creator.create_control_board_message_string(
            name=self.current_track_name,
            song_timer=int(self.song_timer),
            track_duration=int(self.current_track_duration),
            url=self.current_thumbnail
        )
        for msg in self.control_board_messages:
            old_fields = msg.embeds[0].fields
            new_fields = new_embed.fields
            if len(old_fields) != len(new_fields) or not all(old_fields[e].value == new_fields[e].value for e in range(len(old_fields))):
                await msg.edit(embed=new_embed)
    
    async def update_lyrics(self):

        while self.current_lyrics_index < len(self.current_lyrics) - 1 and self.current_lyrics[self.current_lyrics_index + 1].seconds <= self.current_track_duration:
            self.current_lyrics_index += 1
        
        new_msg = string_creator.create_current_lyrics_message(self.current_lyrics, self.current_lyrics_index)

        for msg in self.lyrics_messages:
            try:
                if msg.content != new_msg:
                    await msg.edit(content=new_msg)
            except Exception as e:
                log.error("Couldn't edit lyrics. " + str(e))


    @tasks.loop(count=1)
    async def check_player(self) -> None:
        '''
        Plays the next track, if all conditions are met
        '''

        log.info("Checking whether to play audio")

        # Check whether connected to voice self
        if self.vc and not self.force_stop:

            # Bypass steps if boption available
            if not self.boption:

                # Check whether previous song has ended
                if self.vc.is_playing() or self.vc.is_paused():

                    log.warning("check_player was called although song hasn't ended yet")

                    return

                # Get index of last song in queuelist
                index = self.db.get_max_queue_id()
        
            # Check if more songs are available. bypass if boption available
            if self.boption or (index and index >= self.queue_counter):
                
                # Get and play next song
                while True:
                    try:
                        db_result = self.db.execute(f"SELECT path, length, url, name FROM queuelist WHERE queue_id = {self.queue_counter}")
                        path = db_result[0][0]
                        url = db_result[0][2]
                        break
                    except IndexError:
                        log.warning("Gap in queue_id list!")
                        self.queue_counter += 1
                
                if path == '':
                    if self.boption:
                        source = await YTDLSource.from_url(url, loop=self.loop, before_options=self.boption, stream=True)

                    else:
                        source = await YTDLSource.from_url(url, loop=self.loop, stream=True)

                else:
                    log.info("Playing downloaded song")
                    if self.boption:
                        source = discord.FFmpegOpusAudio(
                            path,
                            before_options=self.boption
                        )

                    else:
                        source = discord.FFmpegOpusAudio(path)

                self.boption = False
                # Reset song timer
                self.song_timer = 0

                await asyncio.sleep(0.5)
                # Play song
                log.info("Playing song")
                self.vc.play(source, after=self.song_done)

                # Stop waiting if was waiting
                self.waiting = False

                # Get name of current track
                self.current_track_name = db_result[0][3]
                
                # Set track duration in self
                self.current_track_duration = db_result[0][1]

                # Set track thumbnail
                _id = convert_url(db_result[0][2], id_only=True)
                self.current_thumbnail = f"https://i.ytimg.com/vi/{_id}/mqdefault.jpg"

            else:

                log.info(f"No more tracks available! Current index: {index}, current queuecounter: {self.queue_counter}")

                # Wait for next track
                self.waiting = True
                self.reset_current_song_data()

                # Update control board message
                await self.send_updated_control_board_messages()
            
            # Update self queue messages
            await self.update_queuelist_messages()
            
            if len(self.lyrics_messages) > 0 and not self.repeat:

                await self.delete_lyrics_messages()

        elif self.force_stop:
            log.warning("Player currently stopped")

        else:
            log.warning("Not connected to voice channel")
        
    @tasks.loop(seconds=0.5)
    async def update_duration(self):

        # TODO test other method
        # Add half a second to the duration timer if the player is currently playing
        if self.vc and self.vc.is_playing():
            self.song_timer += 0.5

            # Check if current song timer is at a whole number and whether the name of the song is available
            if round(self.song_timer * 2) % 2 == 0 and self.current_track_name:
                
                if len(self.control_board_messages):

                    await self.send_updated_control_board_messages()
            
            if len(self.lyrics_messages):
                
                await self.update_lyrics()
    
