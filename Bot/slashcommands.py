'''
Stores all http requests for uploading/updating slash commands
'''
from typing import final
from discord import player
import requests
from dotenv import load_dotenv
import os
import json

import logging
log = logging.getLogger(__name__)

# Load discord token
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Get url
url = "https://discord.com/api/v8/applications/697051009138163732/guilds/456109062833176598/commands"
# url = "https://discord.com/api/v8/applications/697051009138163732/guilds/387214698757750784/commands"

# Create header
headers = {
    "Authorization": f"Bot {TOKEN}"
}


# region functions
def get_playlist_command(choice: list = []) -> dict:
    '''
    Create the playlist slash command http request
    The passed choices will be uploaded as the possible options when selecting a downloaded playlist
    '''

    playlist = {
        "name": "playlist",
        "description": "Adds the contents of a playlist to the queue",
        "options": [
            {
                "name": "url",
                "description": "The url of the playlist",
                "type": 3
            },
            {
                "name": "name",
                "description": "The name of the playlist",
                "type": 3,
                "choices": choice
            },
            {
                "name": "index",
                "description": "At which position in queue",
                "type": 4
            },
            {
                "name": "limit",
                "description": "How many songs do you want to add to queue",
                "type": 4
            },
            {
                "name": "randomize",
                "description": "Randomize the order of songs",
                "type": 5
            }
        ]
    }

    return playlist


def get_delete_command(choice: list = []) -> dict:
    '''
    Create the delete slash command http request
    The passed choices will be uploaded as the possible options when selecting a downloaded playlist
    '''

    delete = {
        "name": "delete",
        "description": "Delete something",
        "options": [
            {
                "name": "playlist",
                "description": "Delete a playlist. Pauses player temporarily (Admin only)",
                "type": 1,
                "options": [
                    {
                        "name": "name",
                        "description": "The name of the playlist",
                        "type": 3,
                        "required": True,
                        "choices": choice
                    }
                ]
            }
        ]
    }
    return delete


def get_update_command(choice: list = []) -> dict:
    '''
    Create the update slash command http request
    The passed choices will be uploaded as the possible options when selecting a downloaded playlist
    '''

    update = {
        "name": "update",
        "description": "Update something",
        "options": [
            {
                "name": "playlist",
                "description": "Update a playlist. Pauses player temporarily (Admin only)",
                "type": 1,
                "options": [
                    {
                        "name": "name",
                        "description": "The name of the playlist",
                        "type": 3,
                        "required": True,
                        "choices": choice
                    },
                    {
                        "name": "url",
                        "description": "Add contents of which playlist or video",
                        "type": 3,
                        "required": False
                    }
                ]
            }
        ]
    }
    return update
# endregion


# region commands
test = {
    "name": "test",
    "description": "Send a random adorable animal photo",
    "options": [
        {
            "name": "animal",
            "description": "The type of animal",
            "type": 3,
            "required": True,
            "choices": [
                {
                    "name": "Dog",
                    "value": "animal_dog"
                },
                {
                    "name": "Cat",
                    "value": "animal_cat"
                },
                {
                    "name": "Penguin",
                    "value": "animal_penguin"
                }
            ]
        },
        {
            "name": "only_smol",
            "description": "Whether to show only baby animals",
            "type": 5,
            "required": False
        }
    ]
}

play = {
    "name": "play",
    "description": "Plays music. Note: You must be in a channel!",
    "options": [
        {
            "name": "name",
            "description": "The name of the video",
            "type": 3
        },
        {
            "name": "url",
            "description": "The url of the video",
            "type": 3
        },
        {
            "name": "amount",
            "description": "The number of results when playing by name. Default value is 1",
            "type": 4
        },
        {
            "name": "index",
            "description": "At which position in queue",
            "type": 4
        }
    ]
}

control = {
    "name": "control",
    "description": "Show the control panel"
}

skip = {
    "name": "skip",
    "description": "Skip a song",
    "options": [
        {
            "name": "amount",
            "description": "Amount of songs to be skipped",
            "type": 4,
            "required": False
        }
    ]
}

back = {
    "name": "back",
    "description": "Play a previous song",
    "options": [
        {
            "name": "amount",
            "description": "How many songs",
            "type": 4,
            "required": False
        }
    ]
}

fast_forward = {
    "name": "fast_forward",
    "description": "Fast forward a song",
    "options": [
        {
            "name": "amount",
            "description": "How many seconds",
            "type": 4,
            "required": False
        }
    ]
}

rewind = {
    "name": "rewind",
    "description": "Rewind a song",
    "options": [
        {
            "name": "amount",
            "description": "How many seconds",
            "type": 4,
            "required": False
        }
    ]
}

pause = {
    "name": "pause",
    "description": "Pause or resume a song"
}

stop = {
    "name": "stop",
    "description": "Stop the player and remove all songs"
}

queue = {
    "name": "queue",
    "description": "Get the queuelist",
    "options": [
        {
            "name": "amount",
            "description": "How many entries do you want to see",
            "type": 4,
            "required": False
        }
    ]
}

create = {
    "name": "create",
    "description": "Create something",
    "options": [
        {
            "name": "playlist",
            "description": "Create a playlist. Pauses player temporarily (Admin only)",
            "type": 1,
            "options": [
                {
                    "name": "url",
                    "description": "The url of the playlist",
                    "type": 3,
                    "required": True
                },
                {
                    "name": "name",
                    "description": "The name of the playlist",
                    "type": 3,
                    "required": True
                }
            ]
        }
    ]
}

_quit = {
    "name": "quit",
    "description": "Close the bot (Admin only)"
}

repeat = {
    "name": "repeat",
    "description": "Repeat or stop repeating a song",
    "options": [
        {
            "name": "amount",
            "description": "How often",
            "type": 4,
            "required": False
        }
    ]
}

shuffle = {
    "name": "shuffle",
    "description": "Shuffles the playlist"
}

lyrics = {
    "name": "lyrics",
    "description": "Shows the lyrics",
    "options": [{
        "name": "full",
        "description": "View all lyrics at once. Show lyrics in sync with music otherwise. False if omitted",
        "type": 5
    }]
}

update = get_update_command()

delete = get_delete_command()
# endregion


def post(js):
    '''
    Post new slash command
    '''
    global url
    global headers

    r = requests.post(url, headers=headers, json=js)
    log.info("Command was sent: " + str(r.content))
    print(r.content)


def get() -> str:
    '''
    Get all currently active slash commands
    '''
    global url
    global headers
    global json
    r = requests.get(url, headers=headers)
    return r.text


def update_playlist_commands() -> None:
    '''
    Updates all commands that contain choices based on the downloaded playlists
    '''

    from file_manager import get_playlists

    # Get all playlists that have an existing directory
    choices = get_playlists()

    # Convert the list elements to the right format
    choices = list(({"name": f"{e}", "value": f"{e}"} for e in choices))

    # Create play, update and delete commands with new playlist choices
    play = get_playlist_command(choices)
    update = get_update_command(choices)
    delete = get_delete_command(choices)

    # Send commands
    post(play)
    post(update)
    post(delete)

    log.info('Updated playlist commands')


if __name__ == "__main__":
    pass

# TODO get server url
