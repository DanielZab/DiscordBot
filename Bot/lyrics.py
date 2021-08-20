from env_vars import EnvVariables
from typing import List
from my_client import MyClient
from discord_slash.context import SlashContext
from youtube import YouTube
import json
import youtube_dl
import logging
import requests
import functools
import asyncio
import lyricsgenius
import re
from downloader import dl_captions

log = logging.getLogger(__name__)


class LyricPoint:
    def __init__(self, text: str, seconds: int) -> None:
        self.text = text
        self.seconds = seconds


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
                    return

                log.info(f"Rection received: {reaction} by {user}")
                
                # Get index of emoji in emoji_list
                emoji_index = client.emoji_list.index(str(reaction))

                # Check if it is the cancel emoji
                if emoji_index == len(client.emoji_list) - 1:

                    await ctx.send("Download was cancelled")
                    log.info("Download was cancelled")
                    return

                language = languages[emoji_index]

                log.info(f"{language} was chosen")

                # Download captions
                caption_path = await dl_captions("https://www.youtube.com/watch?v=" + _id, language)

                # Return file path
                if caption_path:
                    return "caption", caption_path

    else:
        
        data = await get_song_data(_id)

        textyl_lyrics = await get_textyl_lyrics(data[0], data[1])

        if textyl_lyrics:
            return textyl_lyrics
        
        if data[0]:
            genius_lyrics = await get_genius_lyrics(_id, artist=data[0], track=data[1])
            return "genius", genius_lyrics
        else:
            log.warning("Couldn't find lyrics")
            await ctx.send("Couldn't find available lyrics!")


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
        log.warning("Artist and track not found")
        return False, info["title"]


async def get_textyl_lyrics(artist, track) -> tuple:

    # Define different song name and artist combinations
    combinations = [track + " " + artist, artist + " " + track, track]

    log.info("textyl combinations: " + ", ".join(combinations))

    loop = asyncio.get_event_loop()
    # Try to get lyrics using textyl api
    for combination in combinations:
        request = functools.partial(requests.get,
                                   "https://api.textyl.co/api/lyrics?q=" + combination)
        r = await loop.run_in_executor(request)
        if r.text != "No lyrics available":
            return "textyl", r.text
    
    # Convert strings
    artist = convert(artist)
    track = convert(track)

    # Try again using converted strings
    combinations = [track + " " + artist, artist + " " + track, track]

    log.info("textyl combinations: " + ", ".join(combinations))

    for combination in combinations:
        request = functools.partial(requests.get,
                                   "https://api.textyl.co/api/lyrics?q=" + combination)
        r = await loop.run_in_executor(request)
        if r.text != "No lyrics available":
            return "textyl", r.text
    

def convert(s: str):
    
    # Define all brackets
    brackets = ["[]", "()", "{}"]

    # Define all reserved chars in url
    reserved_chars = "!*'();:@&=+$,/?#[]%"

    # Remove all contents in brackets
    while any(e[0] in s and e[1] in s for e in brackets):
        
        # Determine bracket
        for bracket in brackets:
            if bracket[0] in s and bracket[1] in s:
                break

        # Find indices of left and right bracket
        left = s.find(bracket[0])
        right = s.find(bracket[1], left)

        # Check if both brackets were found
        if not (left == -1 or right == -1):

            # Remove substring
            s = s[: left] + s[right + 1:]
        # Remove bracket from bracketlist
        else:
            brackets.remove(bracket)
    
    #Remove all reserved chars
    for c in reserved_chars:
        s = s.replace(c, "")
    
    # Remove double whitespaces
    while s.find("  ") != -1:
        s = s.replace("  ", " ")
    
    # Remove whitespaces at start and end
    s = s.strip()

    # Replace all whitespaces with the url equivalent '%20'
    s.replace(" ", "%20")
    return s


def create_lyrics_list(source: str, current_lyrics: str) -> List[LyricPoint]:

    if source == "textyl":
        json_list = json.loads(current_lyrics)
        lyrics_list = []
        for entry in json_list:
            lyrics_list.append(LyricPoint(entry["lyrics"], int(entry["seconds"])))
        lyrics_list.sort(key=lambda x: x.seconds)
        return lyrics_list
    
    elif source == "captions":

        lyrics_list = []
        with open(current_lyrics, "r") as f:

            for line in f.readlines():

                line = line.strip()

                match = re.match(r"^(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}).(?P<mm>\d{3}) --> [0-9\.:]{12}$", line)

                if match:
                    seconds = int(int(match.group("h")) * 3600 + int(match.group("m")) * 60 + int(match.group("s")))
                    lyrics_list.append(LyricPoint("", seconds))
                elif len(lyrics_list) > 0 and line != "":
                    last_point = lyrics_list[-1]
                    if last_point.text != "":
                        last_point.text += ". "
                    last_point.text += line
        
        return lyrics_list


async def get_genius_lyrics(_id: str, env: EnvVariables, artist: str = None, track: str = None) -> str:

    GENIUS_TOKEN = env.GENIUS_TOKEN

    # Instanciate lyricsgenius client
    genius = lyricsgenius.Genius(GENIUS_TOKEN)

    # Get song data if necessary
    if not track:
        artist, track = get_song_data(_id)
    
    # Set function parameters
    genius_func = functools.partial(genius.search_song,
                                    track,
                                    artist=artist)
    
    # Execute lyrics search
    loop = asyncio.get_event_loop()
    return str(loop.run_in_executor(None, genius_func))
