'''
Tries to get lyrics
'''
from env_vars import EnvVariables
from typing import List
from my_client import MyClient
from discord_slash.context import SlashContext
from lrc_kit import ComboLyricsProvider, SearchRequest
from youtube import YouTube
import youtube_dl
import logging
import functools
import asyncio
import lyricsgenius
import re
from downloader import dl_captions
from youtube_title_parse import get_artist_title

log = logging.getLogger(__name__)


class LyricPoint:
    '''
    Contains information about one verse
    Parameters:
        text:       The actual verse
        seconds:    When does the verse appear in the song
    '''

    def __init__(self, text: str, seconds: int) -> None:
        self.text = text
        self.seconds = seconds

    def __str__(self) -> str:
        '''
        When this object gets converted into a string, return its text
        '''
        return self.text


async def get_lyrics(ctx: SlashContext, _id: str, client: MyClient, yt: YouTube, env: EnvVariables) -> tuple:
    '''
    Tries to get song lyrics from various sources
    Returns a tuple containing the lyrics source and
    the lyrics if successful
    '''

    # Get youtube captions if available
    captions = await yt.get_captions(_id)

    # Check if captions were found
    if captions:

        # Check if only one version of captions exist
        if len(captions) == 1:

            # Download captions
            caption_path = await dl_captions("https://www.youtube.com/watch?v=" + _id, captions[0][1])

            # Return source and file path
            if caption_path:
                return "caption", caption_path

        else:

            # Get all caption languages
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

                # Return source and file path
                if caption_path:
                    return "caption", caption_path

            # Let the user choose a language
            else:

                # Create and send message
                msg = "Found multiple languages. Which one do you want?"
                for i, l in enumerate(languages):
                    msg += f"\n\t{i + 1}. {l}"
                msg = await ctx.send(msg)

                # Add reactions so the member can choose a language
                for i in range(len(languages)):
                    await msg.add_reaction(client.emoji_list[i])

                # Add the cancel emoji
                await msg.add_reaction(client.emoji_list[-1])

                # Define the criteria that must be met for the reaction to be accepted
                def check(reaction, user):
                    log.info(f"Got response: {str(reaction)}")
                    return str(reaction) in client.emoji_list and ctx.author.id == user.id and reaction.message.id == msg.id

                # Wait for reaction
                try:

                    log.info("Waiting for reaction")
                    reaction, user = await client.wait_for('reaction_add', check=check, timeout=200)

                except TimeoutError:

                    log.warning("No reaction has been made")
                    return None, None

                log.info(f"Valid reaction received: {reaction} by {user}")

                # Determine which reaction was made
                emoji_index = client.emoji_list.index(str(reaction))

                # Check if process was cancelled
                if emoji_index == len(client.emoji_list) - 1:
                    log.info("Captions download was cancelled")
                    return "cancelled", None

                # Get corresponding language
                language = languages[emoji_index]

                log.info(f"{language} was chosen")

                # Download captions
                caption_path = await dl_captions("https://www.youtube.com/watch?v=" + _id, language)

                # Return source and file path
                if caption_path:
                    return "caption", caption_path

    # Try to get title and artist from the 'music in this video' section
    # in the video's description
    data = await get_song_data(_id)

    # Get lyrics via lrc-kit library
    log.info("Trying to get lrc-kit lyrics")
    lrc_lyrics = get_lrc(data[0], data[1])

    # Check if lyrics were found
    if lrc_lyrics:

        # Return source and file path
        return 'lrc', lrc_lyrics

    # Get lyrics via lyricsgenius
    genius_lyrics = await get_genius_lyrics(_id, env, artist=data[0], track=data[1])

    # Check if lyrics were found
    if genius_lyrics:
        return "genius", genius_lyrics

    log.warning("Couldn't find lyrics")
    return None, None


def get_lrc(artist: str, song: str) -> str:
    '''
    Tries to get lyrics through the lrc_kit library
    and returns the result
    '''

    # Create lyrics engine
    engine = ComboLyricsProvider()

    # Specify search query
    search = SearchRequest(artist, song)

    # Execute search
    result = engine.search(search)

    if result:
        return str(result)


def get_data_from_title(title: str) -> tuple:
    '''
    Attempts to extract the song title and artists from the video title
    '''

    artist, title = get_artist_title(title)

    return artist, title


async def get_song_data(_id: str) -> tuple:
    '''
    Attempts to get song author and title
    '''

    # Set youtube-dl settings
    ydl = youtube_dl.YoutubeDL({})

    with ydl:

        # Extract youtube video details with youtube-dl
        loop = asyncio.get_event_loop()
        dl_function = functools.partial(ydl.extract_info,
                                        "https://www.youtube.com/watch?v=" + _id,
                                        download=False)
        info = await loop.run_in_executor(None, dl_function)

    try:

        # Try to get artist and track attributes from the results
        artist, track = info["artist"], info["track"]
        return artist, track

    except KeyError:

        # Try to get the artist and song title from the video title
        log.warning("Artist and track not found, trying to get data from title")
        return get_data_from_title(info["title"])


def create_lyrics_list(source: str, current_lyrics: str) -> List[LyricPoint]:
    '''
    Extracts verses and timestamps and creates a list of LyricsPoint objects
    and returns the result
    '''

    # Check if lyrics source are the youtube captions
    if source == "caption":

        lyrics_list = []

        # Open lyrcis file
        with open(current_lyrics, "r", encoding='utf8', errors='ignore') as f:

            for line in f.readlines():

                # Remove whitespaces at both ends of string
                line = line.strip()

                # Match regex pattern for timestamps
                match = re.match(r"^(?P<h>\d{2}):(?P<m>\d{2}):(?P<s>\d{2}).(?P<mm>\d{3}) --> [0-9\.:]{12}.*$", line)

                # Check if timestamps were found
                if match:
                    # Extract time data
                    seconds = int(match.group("h")) * 3600 + int(match.group("m")) * 60 + int(match.group("s")) + int(match.group("mm")) / 1000
                    lyrics_list.append(LyricPoint("", seconds))

                # Otherwise check if any LyricsPoints exist already and if line isn't empty
                elif len(lyrics_list) > 0 and not re.match(r"^\s*$", line):

                    # Get the last LyricPoint
                    last_point = lyrics_list[-1]

                    # Add a whitespace to the LyricPoint's text if it already contains text
                    if last_point.text != "":
                        last_point.text += " "

                    # Add verse to the last LyricsPoint's text
                    last_point.text += line

        # Remove all LyricPoints without a verse
        final_lyrics_list = list(filter(lambda x: x.text != '', lyrics_list))

        return final_lyrics_list

    # Check if lyrics source is the lrc-kit library
    elif source == "lrc":

        lyrics_list = []

        # Split the lyrics into its verses and iterate through every line
        current_lyrics_list = current_lyrics.split("\n")
        for entry in current_lyrics_list:

            # Match regex pattern for timestamps and verses
            match = re.match(r"^\[.*(?P<m>\d{2}):(?P<s>\d{2})\.(?P<mm>\d{3})\](?P<text>.*)$", entry)
            if match:

                # Convert timestamp into seconds, get verse and create a LyricPoint
                seconds = int(match.group("m")) * 60 + int(match.group("s")) + int(match.group("mm")) / 1000
                text = match.group("text")
                lp = LyricPoint(text, seconds)
                lyrics_list.append(lp)

        # Remove all LyricPoints without a verse
        final_lyrics_list = list(filter(lambda x: x.text != '', lyrics_list))

        return final_lyrics_list

    log.critical(f"Unknown current lyrics object: {source}, {current_lyrics}")


async def get_genius_lyrics(_id: str, env: EnvVariables, artist: str = None, track: str = None) -> str:
    '''
    Get lyrics through the genius library
    '''

    # Get genius token
    GENIUS_TOKEN = env.GENIUS_TOKEN

    # Instanciate lyricsgenius client
    genius = lyricsgenius.Genius(GENIUS_TOKEN)

    # Get song data if necessary
    if not track:
        artist, track = await get_song_data(_id)

    # Set function parameters
    if artist:
        genius_func = functools.partial(genius.search_song,
                                        track,
                                        artist=artist)
    else:
        genius_func = functools.partial(genius.search_song,
                                        track)

    # Execute lyrics search
    loop = asyncio.get_event_loop()
    return str(loop.run_in_executor(None, genius_func))
