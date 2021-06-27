import asyncio
import main, database
import discord
import logging
import file_manager
from typing import Union
from discord_slash import SlashContext, ComponentContext

log = logging.getLogger(__name__)


class ControlBoard:

    async def skip(self, client: main.MyClient, db: database.DataBase, ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:

        # Try to get highest index
        try:
            query = "SELECT MAX(queue_id) FROM queuelist;"
            index = db.execute(query)[0][0] - client.queue_counter

            # Check if there are songs to skip
            if index < 1:
                log.warning("No song to skip!")
                await ctx.send("No song to skip", hidden=True)
                return

        except Exception as e:
            log.error("Error when trying to get highest id: " + str(e))
            await ctx.send("No song in queue!", hidden=True)
            return

        if amount < 1:
            amount = 0

        # Limit maximum amount to index
        if not amount <= index:
            amount = index
        
        client.queue_counter += (amount - 1)
        client.vc.stop()

        await ctx.send("Skipped!", hidden=True)

    async def back(self, client: main.MyClient, db: database.DataBase, ctx: Union[SlashContext, ComponentContext], amount: int = 1) -> None:

        # Convert queue:counter to zero-based numbering
        index = client.queue_counter - 1

        # Check if there are previous songs
        if index < 1:
            log.warning("No previous song!")
            await ctx.send("No previous song!", hidden=True)
            return

        # Limit maximum amount to index
        if not amount <= index:
            amount = index
        
        # Select desired song index
        client.queue_counter -= (amount + 1)

        # Stop current song
        client.vc.stop()

        await ctx.send("Playing previous track!", hidden=True)

    async def pause(self, client: main.MyClient, db: database.DataBase, ctx: Union[SlashContext, ComponentContext]) -> None:

        log.info("Toggle pause/resume")

        if client.vc and client.vc.is_paused():
            client.vc.resume()
            await ctx.send("Resumed!", hidden=True)

        elif client.vc and client.vc.is_playing():
            client.vc.pause()
            await ctx.send("Paused!", hidden=True)

        else:
            log.warning("Could not pause, currently no track playing")
            await ctx.send("No song playing!", hidden=True)

    async def fast_forward(self, client: main.MyClient, db: database.DataBase, ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:
        '''
        Fasts forward a song. Skips 10 seconds by default
        '''
        # Get desired timeframe
        destination_time = int(client.song_duration + amount)
        print(destination_time)

        await ctx.defer()

        # Set player configuration
        boption = "-nostdin -ss {}".format(main.format_time_ffmpeg(destination_time))

        # Fast forward
        if not client.play_with_boption(boption):
            log.warning("Fast forward was called although not playing audio")
            await ctx.send("Not playing audio!", hidden=True)
            return

        # Wait until playing the next song
        while not (client.vc.is_playing() or client.vc.is_paused()):
            await asyncio.sleep(0.1)

        client.set_duration_timer(destination_time)
        
        log.info(f"Skipped {amount} seconds")
        await ctx.send("Fast forward complete", hidden=True)

    async def rewind(self, client: main.MyClient, db: database.DataBase, ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:
        '''
        Rewinds a song. Rewinds 10 seconds by default
        '''
        # Get desired timeframe
        destination_time = int(client.song_duration - amount)

        # Set player configuration
        boption = "-nostdin -ss {}".format(main.format_time_ffmpeg(destination_time))

        await ctx.defer()

        # Fast forward
        if not client.play_with_boption(boption):
            log.warning("Rewind was called although not playing audio")
            await ctx.send("Not playing audio!", hidden=True)
            return

        # Wait until playing the next song
        while not (client.vc.is_playing() or client.vc.is_paused()):
            await asyncio.sleep(0.1)

        client.set_duration_timer(destination_time)

        log.info(f"Rewinded {amount} seconds")
        await ctx.send("Rewind complete", hidden=True)


    async def stop(self, client: main.MyClient, db: database.DataBase, ctx: Union[SlashContext, ComponentContext]):

        db.setup()
        file_manager.reset_directories()

        if client.vc_check():
            client.stop()
        
        client.setup()

        log.info("Player was stopped")
        await ctx.send("The player was stopped")

        # TODO fix stop