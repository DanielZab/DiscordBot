# region imports
# High priority imports
import logging
import logger
import hide

# Standard library imports
import os, shutil, datetime, sys, random, time, math, re

# Google and discord api imports
import discord
from discord.ext import tasks, commands
from discord_slash import SlashCommand, SlashContext
import googleapiclient.discovery

# Audio file imports
from pydub import AudioSegment
import audioread
from pydub.utils import which

# Environment variables
from dotenv import load_dotenv

# Other imports
import lyricsgenius, psutil
import mysql.connector
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
                 boption) -> None:
        self.name = name
        self.url = url
        self.length = length
        self.path = path
        self.downloaded = downloaded
        self.boption = boption


class MyClient(discord.Client):
    def __init__(self) -> None:
        super().__init__()
        self.channel = None
        self.vc = None
# endregion


# Get environment variables
env_var = EnvVariables()

connection = mysql.connector.connect(host='localhost',
                                    database='musikbot',
                                    user=env_var.SQL_USER,
                                    password=env_var.SQL_PW)
cursor = connection.cursor()
now = time.localtime()

query = "DELETE FROM queuelist;"
result = cursor.execute(query)
connection.commit()
query = "ALTER TABLE queuelist AUTO_INCREMENT = 1;"
result = cursor.execute(query)
connection.commit()

f = '%Y-%m-%d %H:%M:%S'
t = time.strftime(f, now)
print(t)
query = f"INSERT INTO queuelist (url, path, length, last_played) VALUES ('URL', 'PATH', 90, '{t}');"
result = cursor.execute(query)
connection.commit()
print("Printed")
if connection.is_connected():
    cursor.close()
    connection.close()



# Assign clients
client = MyClient()

genius = lyricsgenius.Genius(env_var.GENIUS_TOKEN)

slash = SlashCommand(client)


async def check_admin(ctx: SlashContext):
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


async def join(ctx):
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

        # Move to the requested channel
        log.info("Moving from current channel")
        await client.channel.move_to(channel)
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


@slash.slash(name='play')
async def _play(ctx: SlashContext, name: str):
    '''
    Plays music
    '''

    # Check if user is an admin
    if not await check_admin(ctx):
        return

    if not await join(ctx):
        return

    await ctx.send("Joined successfully")


@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')
    # TODO:Delete past tracks
    if env_var.AUTO_HIDE == 'True':
        hide.hide()
    # TODO:Change status


if __name__ == "__main__":
    client.run(env_var.TOKEN)
