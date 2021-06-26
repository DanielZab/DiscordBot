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

        await ctx.send(client.song_duration)
        # TODO fast forward

    async def rewind(self, client: main.MyClient, db: database.DataBase, ctx: Union[SlashContext, ComponentContext], amount: int = 10) -> None:

        await ctx.send(client.song_duration)
        # TODO rewind

    async def stop(self, client: main.MyClient, db: database.DataBase, ctx: Union[SlashContext, ComponentContext]):

        db.setup()
        file_manager.reset_directories()

        if client.vc and (client.vc.is_playing() or client.vc.is_paused()):
            client.stop()
        
        client.setup()

        await ctx.send("The player was stopped")