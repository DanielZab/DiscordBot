'''
Handles commands which can be called from the control board
'''
import asyncio
import database
from my_client import MyClient
from converter import format_time_ffmpeg
import discord
import logging
import file_manager
from typing import Union
from discord_slash import SlashContext, ComponentContext

log = logging.getLogger(__name__)


class ControlBoard:
    '''
    Contains all control board commands
    '''

    def __init__(self, client: MyClient, db: database.Database) -> None:
        '''
        Client contains the main my_client object
        Db contains the main Database object
        '''
        self.client = client
        self.db = db

    async def skip(self, ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:
        '''
        Skips a specified number of songs, 1 by default.
        The number can be specified with the amount parameter.
        If amount has a value below 0, the current song will restart
        '''

        log.info(f"Skipping {amount} song(s)")

        await ctx.defer()
        
        # Check if playing music and return if not
        if not self.client.vc_check():
            await ctx.send("Currently not playing!")
            return

        # Get number of songs that can be skipped
        max_id = self.db.get_max_queue_id()
        skippable_songs = max_id - self.client.queue_counter

        # Check if there are songs to skip
        if skippable_songs < 1:
            log.warning("No song to skip!")
            await ctx.send("No song to skip", delete_after=3)
            return

        # Set negative values to 0
        if amount < 0:
            amount = 0

        # Check if skipping more songs than possible
        if amount > skippable_songs:
            amount = skippable_songs

        # Check if skipping one or more songs
        if amount:

            # Stop repeating current song
            self.client.stop_repeat()

            # Increase queue counter by amount
            self.client.queue_counter += amount
        
        # Reduce queue counter by one, since its value will be increased
        # in song_done method after song has ended
        self.client.queue_counter -= 1

        # Stop player
        self.client.vc.stop()

        await ctx.send("Skipped!", delete_after=3)

    async def back(self, ctx: Union[SlashContext, ComponentContext], amount: int = 0) -> None:
        '''
        Plays previous song, amount parameter specifies how many songs to rewind.
        If no amount specified, will restart current song if its playing for more than 5 seconds.
        Otherwise, will play previous song
        '''

        await ctx.defer()

        # Convert queue_counter to zero-based numbering
        zero_based_counter = self.client.queue_counter - 1

        # Set negative amount values to 0
        if amount < 0:
            amount = 0

        # Define conditions, that have to be met,
        # in order to restart song instead of playing the previous ones
        repeat_condition = amount == 0 and self.client.vc_check() and self.client.song_timer >= 5

        log.info(f"Going back by {amount}, with repeat_condition {repeat_condition}")
    
        # Check if there are previous songs and not repeating
        if zero_based_counter < 1 and not repeat_condition:
            log.warning("No previous song!")
            await ctx.send("No previous song!", delete_after=3)
            return

        # Limit maximum amount to highest possible amount
        if not amount <= zero_based_counter:
            amount = zero_based_counter

        # Check whether to player previous song
        if not repeat_condition:

            # Set amount to 1 if none was passed
            if amount == 0:
                amount = 1
            
            # Stop repeating in case current song is being repeated
            self.client.stop_repeat()

            # Set queue counter to desired song index
            self.client.queue_counter -= amount

        # Check if currently playing
        if self.client.vc_check():

            # Reduce queue counter by one, since its value will be increased
            # in song_done method after song has ended
            self.client.queue_counter -= 1

            # Stop player
            self.client.vc.stop()

        # Otherwise start player manually
        else:

            # Start player
            self.client.start_player()
        
        await ctx.send("Gone back!", delete_after=3)
        
    async def pause(self, ctx: Union[SlashContext, ComponentContext]) -> None:
        '''
        Pauses/Resumes player
        '''

        log.info("Toggle pause/resume")

        await ctx.defer()

        # Check if player is active
        if not self.client.vc_check():
            log.warning("Could not pause, currently no track playing")
            await ctx.send("No song playing!", delete_after=3)

        # Resume player if paused
        elif self.client.vc.is_paused():
            self.client.vc.resume()
            await ctx.send("Resumed!", delete_after=3)

        # Pause player if playing
        elif self.client.vc.is_playing():
            self.client.vc.pause()
            await ctx.send("Paused!", delete_after=3)
        
        # Error detection
        else:
            log.error("Player neither paused nor playing, although active")
            await ctx.send("Something went wrong")

    async def fast_forward(self, ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:
        '''
        Fasts forward a song. Number of seconds to skip is specified by amount paramter. 
        Skips 10 seconds by default
        '''

        await ctx.defer()

        log.info(f"Skipping {amount} seconds")

        # Get desired timeframe
        destination_time = int(self.client.song_timer + amount)

        # Change destination time to one second before end of song if skipped too much
        if self.client.current_track_duration <= destination_time:
            destination_time = self.client.current_track_duration - 1

        # Set player configuration
        boption = "-nostdin -ss {}".format(format_time_ffmpeg(destination_time))

        # Fast forward if playing audio
        if not self.client.play_with_boption(boption):
            log.warning("Fast forward was called although not playing audio")
            await ctx.send("Not playing audio!")
            return

        # Wait until playing the next song
        while not (self.client.vc.is_playing() or self.client.vc.is_paused()):
            await asyncio.sleep(0.1)

        # Set song timer to current timeframe
        self.client.song_timer = destination_time

        await ctx.send("Fast forward complete", delete_after=3)

    async def rewind(self, ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:
        '''
        Rewinds a song. Number of seconds to rewind is specified by amount paramter. 
        Rewinds 10 seconds by default
        '''

        await ctx.defer()

        log.info(f"Rewinding {amount} seconds")

        # Get desired timeframe
        destination_time = int(self.client.song_timer - amount)

        # If destination time is negative, start playing at start of song
        if destination_time < 0:
            destination_time = 0

        # Set player configuration
        boption = "-nostdin -ss {}".format(format_time_ffmpeg(destination_time))

        # Rewind if playing audio
        if not self.client.play_with_boption(boption):
            log.warning("Rewind was called although not playing audio")
            await ctx.send("Not playing audio!")
            return

        # Wait until playing the next song
        while not (self.client.vc.is_playing() or self.client.vc.is_paused()):
            await asyncio.sleep(0.1)

        # Set song timer to current timeframe
        self.client.song_timer = destination_time

        await ctx.send("Rewind complete", delete_after=3)

    async def stop(self, ctx: Union[SlashContext, ComponentContext], silent=False):
        '''
        Stops the player and resets all data.
        If silent parameter is True, no message will be sent
        '''
        await ctx.defer()
        
        # Check if player is active
        if not self.client.vc_check():
            await ctx.send("Currently not playing audio")
        
        # Reset database data
        self.db.setup()

        # Stop client playback
        self.client.stop()

        # Disconnect from voice channel
        await self.client.disconnect()

        # Delete all messages displaying the control board
        await self.client.delete_control_board_messages()

        # Delete all messages showing the queue list
        await self.client.delete_queuelist_messages()

        # Wait half a second
        await asyncio.sleep(0.5)

        # Reset bot data
        self.client.setup()

        # Reset all directories
        file_manager.reset_directories()

        log.info("Player was stopped")

        # Send message if desired
        if not silent:
            await ctx.send("The player was stopped")
