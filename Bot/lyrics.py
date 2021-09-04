from sys import getrefcount
from env_vars import EnvVariables
from typing import List
from my_client import MyClient
from discord_slash.context import SlashContext
from lrc_kit import ComboLyricsProvider, SearchRequest
from youtube import YouTube
import json
import youtube_dl
import logging
import requests
import functools
import asyncio
import lyricsgenius
import re, os, random
from downloader import dl_captions
from youtube_title_parse import get_artist_title

log = logging.getLogger(__name__)


class LyricPoint:
    def __init__(self, text: str, seconds: int) -> None:
        self.text = text
        self.seconds = seconds
    
    def __str__(self) -> str:
        return self.text


async def get_lyrics(ctx: SlashContext, _id: str, client: MyClient, yt: YouTube, env: EnvVariables) -> tuple:
    '''
    Tries to get song lyrics from various resources
    Returns tuple containing the lyrics source and the lyrics
    '''
    # Get youtube captions if possible
    captions = await yt.get_captions(_id)

    if captions:
        if len(captions) == 1:

            # Download captions
            caption_path = await dl_captions("https://www.youtube.com/watch?v=" + _id, captions[0][1])

            # Return file path
            if caption_path:
                return "caption", caption_path

        else:

            # Get all languages
            languages = []
            for caption_id, language in captions:
                try:
                    languages.index(language)
                except ValueError:
                    languages.append(language)
            
            # Check if all captions have the same language
            if len(languages) == 1:

                # Download captions
                caption_path = await dl_captions("https://www.youtube.com/watch?v=" + _id, captions[0][1])

                # Return file path
                if caption_path:
                    return "caption", caption_path
            
            # Let the user choose a language
            else:

                # Create message
                msg = "Found multiple languages. Which one do you want?"

                for i, l in enumerate(languages):
                    msg += f"\n\t{i + 1}. {l}"

                msg = await ctx.send(msg)

                # Add reactions so the member can choose a language
                for i in range(len(languages)):
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
                    return None, None

                log.info(f"Rection received: {reaction} by {user}")
                
                # Get index of emoji in emoji_list
                emoji_index = client.emoji_list.index(str(reaction))

                # Check if it is the cancel emoji
                if emoji_index == len(client.emoji_list) - 1:

                    log.info("Download was cancelled")
                    return "cancelled", None

                language = languages[emoji_index]

                log.info(f"{language} was chosen")

                # Download captions
                caption_path = await dl_captions("https://www.youtube.com/watch?v=" + _id, language)

                # Return file path
                if caption_path:
                    return "caption", caption_path

    data = await get_song_data(_id)
    
    log.info("Trying to get lrc-kit lyrics")

    lrc_lyrics = get_lrc(data[0], data[1])

    if lrc_lyrics:
        return 'lrc', lrc_lyrics
    
    log.info("Trying to get textyl_lyrics")

    textyl_lyrics = await get_textyl_lyrics(data[0], data[1])

    if textyl_lyrics:
        return "textyl", textyl_lyrics

    if data[0]:
        genius_lyrics = await get_genius_lyrics(_id, artist=data[0], track=data[1])
        return "genius", genius_lyrics
    
    log.warning("Couldn't find lyrics")
    return None, None


def get_lrc(artist: str, song: str):
    engine = ComboLyricsProvider()
    search = SearchRequest(artist, song)
    result = engine.search(search)

    if result:
        return str(result)
    
    return None


def get_data_from_title(title: str) -> tuple:
    artist, title = get_artist_title(title)

    if not (artist and title):
        return False, title

    return artist, title


async def get_song_data(_id: str) -> tuple:
    '''
    Try to get author and name of track with youtube-dl
    '''

    ydl = youtube_dl.YoutubeDL({})

    with ydl:
        loop = asyncio.get_event_loop()
        dl_function = functools.partial(ydl.extract_info,
                                        "https://www.youtube.com/watch?v=" + _id,
                                        download=False)

        info = await loop.run_in_executor(None, dl_function)

    try:

        artist, track = info["artist"], info["track"]
        return artist, track

    except KeyError:
        log.warning("Artist and track not found, trying to get data from title")
        return get_data_from_title(info["title"])


async def get_textyl_lyrics(artist, track) -> tuple:

    # Define different song name and artist combinations
    combinations = [track + " " + artist, artist + " " + track, track]

    log.info("textyl combinations: " + ", ".join(combinations))

    loop = asyncio.get_event_loop()
    # Try to get lyrics using textyl api
    for combination in combinations:
        request = functools.partial(requests.get,
                                   "https://api.textyl.co/api/lyrics?q=" + combination)
        r = await loop.run_in_executor(None, request)
        if r.text != "No lyrics available" and not (400 <= r.status_code <= 600):
            return r.text


def create_lyrics_list(source: str, current_lyrics: str) -> List[LyricPoint]:

    if source == "textyl":
        json_list = json.loads(current_lyrics)
        lyrics_list = []
        for entry in json_list:
            lyrics_list.append(LyricPoint(entry["lyrics"], int(entry["seconds"])))
        lyrics_list.sort(key=lambda x: x.seconds)
        return lyrics_list
    
    elif source == "caption":

        lyrics_list = []
        with open(current_lyrics, "r", encoding='utf8', errors='ignore') as f:

            for line in f.readlines():

                line = line.strip()

                match = re.match(r"^(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}).(?P<mm>\d{3}) --> [0-9\.:]{12}.*$", line)

                if match:
                    seconds = int(match.group("h")) * 3600 + int(match.group("m")) * 60 + int(match.group("s")) + int(match.group("mm")) / 1000
                    lyrics_list.append(LyricPoint("", seconds))
                elif len(lyrics_list) > 0 and line not in ["", " ", "  "]:
                    last_point = lyrics_list[-1]
                    if last_point.text != "":
                        last_point.text += " "
                    last_point.text += line
        
        return lyrics_list
    
    elif source == "lrc":
        final_lyrics_list = []
        current_lyrics_list = current_lyrics.split("\n")
        for entry in current_lyrics_list:
            match = re.match(r"^\[.*(?P<m>\d{2}):(?P<s>\d{2})\.(?P<mm>\d{3})\](?P<text>.*)$", entry)
            if match:
                seconds = int(match.group("m")) * 60 + int(match.group("s")) + int(match.group("mm")) / 1000
                text = match.group("text")
                lp = LyricPoint(text, seconds)
                final_lyrics_list.append(lp)
        
        return final_lyrics_list

    log.critical(f"Unknown current lyrics object: {source}, {current_lyrics}")


async def get_genius_lyrics(_id: str, env: EnvVariables, artist: str = None, track: str = None) -> str:

    GENIUS_TOKEN = env.GENIUS_TOKEN

    # Instanciate lyricsgenius client
    genius = lyricsgenius.Genius(GENIUS_TOKEN)

    # Get song data if necessary
    if not track:
        artist, track = await get_song_data(_id)
    
    # Set function parameters
    genius_func = functools.partial(genius.search_song,
                                    track,
                                    artist=artist)
    
    # Execute lyrics search
    loop = asyncio.get_event_loop()
    return str(loop.run_in_executor(None, genius_func))
