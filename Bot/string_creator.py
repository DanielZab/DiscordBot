'''
Creates strings and brings them into the right format
'''
import logging
from discord import Embed
import tkinter
from tkinter import font as tkFont
from typing import List
from lyricsgenius.api import Song
log = logging.getLogger(__name__)

# TODO end of lyrics

def create_queue_string(queuelist: list, amount: int) -> List[str]:
    '''
    Creates queue list string
    '''

    from main import convert_time

    # Create containers
    msg_list = []
    new_msg = ""

    log.info("Creating queuelist string")

    for i, entry in enumerate(queuelist):

        # Get song title
        name = entry[0]

        # Convert song duration and bring it into the right format
        length = convert_time(int(entry[1]))
        length = f"{str(length[0]) + ':' if length[0] else ''}{str(length[1]).zfill(2)}:{str(length[2]).zfill(2)}"
        
        # Limit song title to 60 characters and remove all '*' and '_' chars
        name_string = f"{name if len(name) < 60 else name[:60] + '...'} ({length})"
        name_string = name_string.replace("_", " ").replace("*", " ")

        # Write 'current track' at start of message
        if i == 0:

            new_msg += f"Current track:\n\t\t{name_string}"

        # Create queuelist entry string
        else:

            # Add 'Queue list' before second entry
            if i == 1:
                new_msg += "\nQueue list:"
            
            new_msg += f"\n\t\t{str(i)}. {name_string}"
        
        # Check whether max amount was reached
        if amount == i:
            msg_list.append(new_msg)
            new_msg = ""
            break
        
        # Create new string if message would exceed 20 entries
        elif i % 20 == 0 and i != 0:

            # Add current message to message list
            msg_list.append(new_msg)

            # Create new string
            new_msg = "Continuation:"

    # Check if last message contains any entries
    if new_msg != "Continuation:":

        # Add last message to message list
        msg_list.append(new_msg)

    return msg_list


def create_control_board_message_embed(name: str, song_timer: int, track_duration: int, url: str) -> Embed:
    '''
    Creates control board message embed and returns the result
    Consists of a thumbnail, current track name, a progress bar and six buttons
    '''

    from main import convert_time

    log.debug("Creating control board message string")

    cctd = convert_time(track_duration)  # Converted current track duration

    # Create new embed and set thumbnail
    embed = Embed()
    if url:
        embed.set_thumbnail(url=url)
    
    # Set title of embed to 'No current track' if not playing anything and return embed
    if not name:
        embed.title = "No Current Track"
        return embed

    # Limit title length to 60 chars and append total song duration
    title = f"{name if len(name) < 60 else name[:60] + '...'} ({(cctd[0]+':') if cctd[0] else ''}{str(cctd[1]).zfill(2) + ':' + str(cctd[2]).zfill(2)})"

    # Set song title as embed title
    embed.title = title
    
    # Try to calculate length of title text and adapt the length of the progress bar
    tkinter.Frame().destroy()
    arial16b = tkFont.Font(family='Arial', size=16, weight="bold")
    arial16n = tkFont.Font(family='Arial', size=16, weight="normal")
    title_width = arial16b.measure(title)
    unit_width = arial16n.measure("░")
    length = int(title_width / unit_width) + 1

    # Limit bar length to 39
    if length > 39:
        length = 39
    
    # Create progress bar
    progress_bar = ""
    for i in range(1, length + 1):
        if i / length <= song_timer / (track_duration - 1):
            progress_bar += '█'
        else:
            progress_bar += '░'

    # Add progress bar as a field
    embed.add_field(name="Progress:", value=progress_bar, inline=False)

    return embed


def create_genius_lyrics_message(lyrics: Song) -> List[str]:
    '''
    Create lyrics message from Song object from lyricsgenius api
    '''

    # Split lyrics into lines
    lyrics = lyrics.lyrics
    lyrics_lines = list(filter(lambda x: x != "", lyrics.split('\n')))
    
    # Combine 20 lines to one message
    msg = ""
    final_msg_list = []
    for i, line in enumerate(lyrics_lines):
        if i:
            msg += '\n'
        msg += line

        if i % 20 == 0 and i != 0:
            final_msg_list.append(msg)
            msg = ""
    
    # Append last message to list if not empty
    if msg != "":
        final_msg_list.append(msg)
    
    return final_msg_list


def create_current_lyrics_message(lyrics: list, index: int) -> str:
    '''
    Creates a message containing 5 verses of the current sync.
    Optimally, the 3rd verse is the current one
    '''

    # Check if song has less tha n 5 verses
    if len(lyrics) < 5:
        return '\n'.join(list(str(e) for e in lyrics))

    # Indicates which verse to highlight
    highlight_phrase = 2

    # Check if highlighted verse cant be the middle one
    # and determine the position of the current verse
    if index < 2:
        highlight_phrase = index
        index = 2
    elif (len(lyrics) - 1) - index < 3:
        highlight_phrase = 5 - ((len(lyrics) - 1) - index)
        index = len(lyrics) - 3

    # Create string
    msg = ""
    for i, entry in enumerate(lyrics[index - 2: index + 3]):
        
        # Replace all stars and underscores with similar chars
        verse = str(entry).replace('*', '⚹').replace('_', '‗')
        
        # Check if verse is empty
        if verse == "":
            continue

        # Check whether to highligh verse
        if i == highlight_phrase:
            msg += "**" + verse + "**\n"
        
        # Otherwise add verse normally
        else:
            msg += verse + "\n"
    
    # Add two final lines
    msg += "-----------------------------------------------------\n"
    msg += "*Use these buttons to sync the lyrics if out of sync*"

    return msg


def create_playlist_download_string(msg: str, index: int, li: list):
    '''
    Creates a string that show a playlist download progress
    '''

    return f"{msg} ({index}/{len(li)})"
